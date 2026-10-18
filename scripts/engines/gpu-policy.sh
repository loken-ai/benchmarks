#!/usr/bin/env bash
# WHICH CARDS EACH ENGINE MAY USE - one declaration, sourced by every launcher.
#
# The policy was written three times, in three scripts, and drifted: bench-cell.sh gave LOKEN
# the whole machine and restricted ollama to card 0, which is the comparison that scored two
# cards against one. This file exists so a launcher states the policy instead of inventing it.
#
#   gpu_policy_resolve            # reads GPUS / OLLAMA_GPUS / LOKEN_GPUS / VLLM_GPUS
#   gpu_env_for <engine>          # prints the env assignments to prefix that engine's launch
#   gpu_extra_args_for <engine>   # prints the per-engine flags (vLLM --tensor-parallel-size)
#
# GPUS is the policy: a comma-separated list of PHYSICAL card indices, or "all" (default).
# Per-engine overrides exist for the deliberate asymmetric run - a fairness knob you can turn
# the wrong way on purpose is honest; one that is only reachable for a single engine is not.
#
# Cards are exposed by UUID, never by index: CUDA_VISIBLE_DEVICES=0 means a different physical
# card depending on CUDA_DEVICE_ORDER, and every engine here is given PCI_BUS_ID so that the
# indices a caller writes mean the same silicon in all three processes.

GPUS="${GPUS:-all}"
# Whose cards the run measures: nvidia (CUDA, NVML) or amd (ROCm). On a machine with both, the
# other vendor's cards are hidden from every engine, so a cell is one vendor's silicon.
GPU_VENDOR="${GPU_VENDOR:-nvidia}"
OLLAMA_GPUS="${OLLAMA_GPUS:-$GPUS}"
LOKEN_GPUS="${LOKEN_GPUS:-$GPUS}"
VLLM_GPUS="${VLLM_GPUS:-$GPUS}"

# _gpu_uuids <spec> - resolve "all" or "0,2" to the matching UUIDs, in the order asked.
_gpu_uuids() {
    local spec="$1" all uuid i
    all=$(nvidia-smi --query-gpu=uuid --format=csv,noheader 2>/dev/null) || return 1
    [ -z "$all" ] && return 1
    if [ "$spec" = all ]; then printf '%s' "$(echo "$all" | paste -sd,)"; return 0; fi
    local out=""
    for i in ${spec//,/ }; do
        uuid=$(echo "$all" | sed -n "$((i + 1))p")
        [ -z "$uuid" ] && { echo "gpu-policy: no card at index $i" >&2; return 1; }
        out="${out:+$out,}$uuid"
    done
    printf '%s' "$out"
}

# _amd_cards - one line per AMD display card, in the order ROCm numbers them (PCI order).
_amd_cards() {
    local d
    for d in /sys/bus/pci/devices/*; do
        [ "$(cat "$d/vendor" 2>/dev/null)" = 0x1002 ] || continue
        case "$(cat "$d/class" 2>/dev/null)" in 0x0300*|0x0380*) echo "${d##*/}" ;; esac
    done
}

# _gpu_count <spec> - how many cards that spec exposes.
_gpu_count() {
    if [ "$1" != all ]; then echo "$1" | tr ',' '\n' | grep -c .
    elif [ "$GPU_VENDOR" = amd ]; then _amd_cards | grep -c .
    else nvidia-smi --query-gpu=uuid --format=csv,noheader 2>/dev/null | grep -c .; fi
}

# gpu_env_for <ollama|loken|vllm> - the env prefix for that engine's launch.
gpu_env_for() {
    local spec n uuids
    case "$1" in
        ollama) spec="$OLLAMA_GPUS" ;; loken) spec="$LOKEN_GPUS" ;; vllm) spec="$VLLM_GPUS" ;;
        *) echo "gpu_env_for: unknown engine '$1'" >&2; return 1 ;;
    esac
    n=$(_gpu_count "$spec")
    if [ "$GPU_VENDOR" = amd ]; then
        # No NVIDIA card, and the AMD cards by ROCm's own numbering. HIP also reads
        # CUDA_VISIBLE_DEVICES unless HIP_VISIBLE_DEVICES is set, so both are named.
        local amd="$spec"
        [ "$spec" = all ] && amd=$(seq -s, 0 $((n - 1)))
        printf 'CUDA_VISIBLE_DEVICES=-1 HIP_VISIBLE_DEVICES=%s' "$amd"
    else
        uuids=$(_gpu_uuids "$spec") || return 0      # no NVML: leave the environment alone
        printf 'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=%s' "$uuids"
    fi
    # Exposing several cards is not the same as using them: ollama's scheduler will settle on
    # one unless told to spread. Without this, "ollama sees two cards" and "ollama uses two
    # cards" differ, and the second is what the comparison is about.
    [ "$1" = ollama ] && [ "$n" -gt 1 ] && printf ' OLLAMA_SCHED_SPREAD=1'
    return 0
}

# gpu_extra_args_for <engine> - flags that are not environment.
gpu_extra_args_for() {
    local spec n
    case "$1" in
        ollama) spec="$OLLAMA_GPUS" ;; loken) spec="$LOKEN_GPUS" ;; vllm) spec="$VLLM_GPUS" ;;
        *) return 1 ;;
    esac
    n=$(_gpu_count "$spec") || return 0
    # vLLM shards across exactly the cards it was given; anything else leaves them idle.
    [ "$1" = vllm ] && [ "$n" -gt 0 ] && printf -- '--tensor-parallel-size %s' "$n"
    return 0
}

# gpu_policy_banner - print what every engine was actually given, so a run is self-describing.
gpu_policy_banner() {
    printf '  GPUs - ollama:%s  loken:%s  vllm:%s\n' "$OLLAMA_GPUS" "$LOKEN_GPUS" "$VLLM_GPUS" >&2
    if [ "$OLLAMA_GPUS" != "$LOKEN_GPUS" ] || [ "$LOKEN_GPUS" != "$VLLM_GPUS" ]; then
        printf '  ⚠️  engines were given DIFFERENT cards - cells from this run are not like-for-like\n' >&2
    fi
}
