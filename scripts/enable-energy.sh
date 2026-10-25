#!/usr/bin/env bash
# Make the energy of a machine measurable by the campaign, and say what is and is not.
#
#   scripts/enable-energy.sh                 # this machine: install the rule if needed, then report
#   scripts/enable-energy.sh --check         # this machine: report only, change nothing, no root
#   scripts/enable-energy.sh host [host...]  # other machines, over ssh (asks for sudo there)
#   scripts/enable-energy.sh --check host... # other machines: report only
#
# What a run's energy is made of, and where each part is read:
#   processor   RAPL package and dram counters under /sys/class/powercap. The kernel makes them
#               readable by root only; the rule written here makes them readable by everyone.
#   NVIDIA      the NVML energy counter, readable by any user.
#   AMD         the power the amdgpu driver publishes in hwmon, readable by any user, which the
#               measurement integrates over the window.
#   Intel GPU   inside the processor's package domain; nothing separate to read.
#
# The rule is a systemd-tmpfiles entry, so it holds across reboots. The counters are read-only
# values; making them world-readable is the whole change.
#
# Exit status: 0 when every domain of the machine is measurable, 1 when one is not, 2 on misuse.
set -u

RULE_FILE=/etc/tmpfiles.d/loken-bench-rapl.conf
RULE_LINES=(
  'z /sys/class/powercap/intel-rapl:*/energy_uj 0444 root root -'
  'z /sys/class/powercap/intel-rapl-mmio:*/energy_uj 0444 root root -'
)
POWERCAP=/sys/class/powercap

die() { echo "enable-energy: $*" >&2; exit 2; }

rapl_domains() { # one path per energy counter of the processor
  local f
  for f in "$POWERCAP"/intel-rapl*/energy_uj "$POWERCAP"/intel-rapl*:*/energy_uj; do
    [ -e "$f" ] && echo "$f"
  done | sort -u
}

readable() { cat "$1" >/dev/null 2>&1; }

# Print what is measurable here. Returns 1 when something is not.
report() {
  local ok=0 f name total=0 open=0
  echo "== $(hostname)"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    total=$((total + 1))
    name="$(cat "$(dirname "$f")/name" 2>/dev/null || echo '?')"
    if readable "$f"; then open=$((open + 1)); echo "  processor  $(basename "$(dirname "$f")")  $name: readable"
    else echo "  processor  $(basename "$(dirname "$f")")  $name: NOT readable"; fi
  done < <(rapl_domains)
  if [ "$total" = 0 ]; then
    echo "  processor  no RAPL counter on this machine: the processor's energy cannot be measured"; ok=1
  elif [ "$open" -lt "$total" ]; then ok=1; fi
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null | grep -q .; then
    echo "  NVIDIA     $(nvidia-smi -L | wc -l) card(s), energy read through NVML"
  fi
  local card dir vendor power any_amd=0
  for card in /sys/class/drm/card[0-9]*; do
    [ -r "$card/device/vendor" ] || continue
    vendor="$(cat "$card/device/vendor")"
    [ "$vendor" = 0x1002 ] || continue
    case "$(cat "$card/device/class" 2>/dev/null)" in 0x0300*|0x0380*) ;; *) continue ;; esac
    # An integrated GPU borrows host memory, and its energy is inside the processor's package
    # domain. The threshold is the one of engines/gpu-policy.sh (CARD_MIN_MIB): below it, not a card.
    if [ $(( $(cat "$card/device/mem_info_vram_total" 2>/dev/null || echo 0) / 1048576 )) -lt 4096 ]; then
      echo "  AMD        ${card##*/}: integrated GPU, its energy is inside the processor's package"
      continue
    fi
    any_amd=1
    power=""
    for dir in "$card"/device/hwmon/hwmon*; do
      for f in energy1_input power1_average power1_input; do
        [ -r "$dir/$f" ] && { power="$f"; break 2; }
      done
    done
    if [ -n "$power" ]; then echo "  AMD        ${card##*/}: power read from hwmon $power"
    else echo "  AMD        ${card##*/}: no power reading in hwmon, its energy cannot be measured"; ok=1; fi
  done
  [ "$any_amd" = 1 ] || true
  [ "$ok" = 0 ] && echo "  => every domain of this machine is measurable" \
                || echo "  => some domain is not measurable; its energy is left out of the records"
  return "$ok"
}

install_rule() { # needs root
  local want current
  want="$(printf '%s\n' "${RULE_LINES[@]}")"
  current="$(cat "$RULE_FILE" 2>/dev/null || true)"
  if [ "$current" != "$want" ]; then
    printf '%s\n' "${RULE_LINES[@]}" > "$RULE_FILE" || return 1
    echo "  wrote $RULE_FILE"
  else
    echo "  $RULE_FILE is already in place"
  fi
  systemd-tmpfiles --create "$RULE_FILE" || return 1
}

here() {
  if [ -z "$(rapl_domains)" ]; then
    report; return $?
  fi
  local missing=0 f
  while IFS= read -r f; do readable "$f" || missing=1; done < <(rapl_domains)
  if [ "$missing" = 1 ] || [ ! -e "$RULE_FILE" ]; then
    if [ "$(id -u)" = 0 ]; then install_rule || die "could not install the rule"
    else
      command -v sudo >/dev/null 2>&1 || die "root is needed to install $RULE_FILE and sudo is absent"
      echo "== $(hostname): installing the rule (sudo)"
      sudo env RULE_FILE="$RULE_FILE" bash "$0" --install || die "could not install the rule"
    fi
  fi
  report
}

mode=""
case "${1:-}" in
  --check) if [ "$#" = 1 ]; then report; exit $?; fi; mode="--check"; shift ;;
  *) ;;
esac
case "${1:-}" in
  --install) install_rule; exit $? ;;
  -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "") here; exit $? ;;
  -*) die "unknown option: $1 (try --help)" ;;
esac

status=0
for host in "$@"; do
  remote="$(ssh "$host" 'mktemp -p "${XDG_RUNTIME_DIR:-/dev/shm}" energy.XXXXXX')" || { echo "enable-energy: cannot reach $host" >&2; status=1; continue; }
  scp -q "$0" "$host:$remote" || { echo "enable-energy: cannot copy the script to $host" >&2; status=1; continue; }
  tty="-t"; [ -n "$mode" ] && tty=""
  # shellcheck disable=SC2086
  ssh $tty "$host" "bash $remote $mode; rc=\$?; rm -f $remote; exit \$rc" || status=1
done
exit "$status"
