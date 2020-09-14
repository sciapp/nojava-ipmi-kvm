# bash completion for `nojava-ipmi-kvm` (hostnames only)

_nojava-ipmi-kvm_completions() {
    local hosts

    _nojava-ipmi-kvm_read_hosts_from_config() {
        python <<-EOF 2>/dev/null
			import os
			import yaml

			with open(os.path.expanduser("~/.nojava-ipmi-kvmrc.yaml"), "r") as config_file:
			    print("\n".join(yaml.safe_load(config_file)["hosts"].keys()))
		EOF
    }

    hosts=( $(_nojava-ipmi-kvm_read_hosts_from_config) )
    COMPREPLY=($(compgen -W "${hosts[*]}" "${COMP_WORDS[1]}"))
}

complete -F _nojava-ipmi-kvm_completions nojava-ipmi-kvm
