# bash completion for `nojava-ipmi-kvm` (hostnames only)

_nojava-ipmi-kvm_completions() {
    local hosts
    hosts=( $(awk '$0~/^\[[^\]]+\]$/ && $0 != "[general]" { print substr($0, 2, length($0)-2) }' ~/.nojava-ipmi-kvmrc 2>/dev/null | sort) )

    COMPREPLY=($(compgen -W "${hosts[*]}" "${COMP_WORDS[1]}"))
}

complete -F _nojava-ipmi-kvm_completions nojava-ipmi-kvm
