#!/usr/bin/env bash

# This is a bash completion script for liquidctl 
# to enable this completion place this file in /etc/bash_completion.d/ (note this locatio may be system dependant_ 
# you can also enable this manually by sourcing this file in your ~/.bashrc file `source path/to/this` 
#
# Created by: Marshall Asch
# updated: October 22, 2020



# logging method
_e() { echo "$1" >> log; }


_list_bus_options () {
    liquidctl list -v | grep 'Bus:' | cut -d ':' -f 2 | sort -u
}

_list_vendor_options () {
    liquidctl list -v | grep 'Vendor ID:' | cut -d ':' -f 2 | cut -c4-6 | sort -u
}

_list_product_options () {
    liquidctl list -v | grep 'Product ID:' | cut -d ':' -f 2 | cut -c4-6 | sort -u
}

_list_device_options () {
    liquidctl list | cut -d ' ' -f 3 | cut -d ':' -f 1 | sort -u
}

_list_match_options () {
    liquidctl list | cut -d ':' -f 2 | sort -u
}

_list_pick_options () {
    num=$(liquidctl list | wc -l)
    seq $num
}

_list_release_options () {
    liquidctl list -v | grep 'Release number:' | cut -d ':' -f 2 | sort -u
}

_list_address_options () {
    liquidctl list -v | grep 'Address:' | cut -d ':' -f 2 | sort -u
}

_list_port_options () {
    liquidctl list -v | grep 'Port:' | cut -d ':' -f 2 | sort -u
}

_list_serial_options () {
    liquidctl list -v | grep 'Serial number:' | cut -d ':' -f 2 | sort -u
}

_liquidctl_main() {


    local commands="
    set
    initialize
    list
    status
    "


    local boolean_options="
    --verbose -v
    --debug -g
    --version
    --help
    --single-12v-ocp
    --legacy-690lc
    "

    local options_with_args="
    --match -m
    --pick -n
    --vendor
    --product
    --release
    --serial
    --bus
    --address
    --usb-port
    --device -d
    --speed
    --time-per-color
    --time-off
    --alert-threshold
    --alert-color
    --pump-mode
    --unsafe
    "
    
    # This part will check if it is currently completing a flag 
    local previous=$3
    local cur="${COMP_WORDS[COMP_CWORD]}"

    case "$previous" in
        --vendor)
            COMPREPLY=($(compgen -W "$(_list_vendor_options)" -- "$cur"))
            return
            ;;
        --product)
            COMPREPLY=($(compgen -W "$(_list_product_options)" -- "$cur"))
            return
            ;;
        --bus)
            COMPREPLY=($(compgen -W "$(_list_bus_options)" -- "$cur"))
            return
            ;;
        --address)
            COMPREPLY=($(compgen -W "$(_list_port_options)" -- "$cur"))
            return
            ;;
        --match | -m )
            COMPREPLY=($(compgen -W "$(_list_match_options)" -- "$cur"))
            return
            ;;
        --pick | -n )
            COMPREPLY=($(compgen -W "$(_list_pick_options)" -- "$cur"))
            return
            ;;
        --device | -d )
            COMPREPLY=($(compgen -W "$(_list_device_options)" -- "$cur"))
            return
            ;;
        --release)
            COMPREPLY=($(compgen -W "$(_list_release_options)" -- "$cur"))
            return
            ;;
        --serial)
            COMPREPLY=($(compgen -W "$(_list_serial_options)" -- "$cur"))
            return
            ;;
        --usb-port)
            COMPREPLY=($(compgen -W "$(_list_port_options)" -- "$cur"))
            return
            ;;
        --speed | --time-per-color | --time-off | --alert-threshold | --alert-color | --unsafe )
            COMPREPLY=()
            return
            ;;
        --pump-mode)
            COMPREPLY=($(compgen -W "balanced quiet extreme" -- "$cur"))
            return
            ;;
        esac


    local i=1 cmd

  # find the subcommand - first word after the flags
  while [[ "$i" -lt "$COMP_CWORD" ]]
  do
      local s="${COMP_WORDS[i]}"
      case "$s" in
          --help | --version)
              COMPREPLY=()
              return
              ;;
          -*) ;;
          initialize | list | status | set )
              cmd="$s"
              break
              ;;
      esac
      (( i++ ))
  done

  if [[ "$i" -eq "$COMP_CWORD" ]]
  then

      COMPREPLY=($(compgen -W "$commands $options_with_args $boolean_options" -- "$cur"))
      return # return early if we're still completing the 'current' command
  fi

  # we've completed the 'current' command and now need to call the next completion function
  # subcommands have their own completion functions
  case "$cmd" in
      list) COMPREPLY=""  ;;
      initialize) _liquidctl_initialize_command ;;
      status) COMPREPLY="" ;;
      set) _liquidctl_set_command ;;
      *)          ;;
  esac
}

_liquidctl_initialize_command ()
{  
    local i=1 subcommand_index

  # find the sub command (either a fan or an led to set)
  while [[ $i -lt $COMP_CWORD ]]; do
      local s="${COMP_WORDS[i]}"
      case "$s" in
          all)
              subcommand_index=$i
              break
              ;;
      esac
      (( i++ ))
  done


  if [[ "$i" -eq "$COMP_CWORD" ]]
  then
      local cur="${COMP_WORDS[COMP_CWORD]}"
      COMPREPLY=($(compgen -W "all" -- "$cur"))
      return # return early if we're still completing the 'current' command
  fi


  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=() #($(compgen -W "all" -- "$cur"))
}


_liquidctl_set_command ()
{
    local i=1 subcommand_index is_fan=-1

  # find the sub command (either a fan or an led to set)
  while [[ $i -lt $COMP_CWORD ]]; do
      local s="${COMP_WORDS[i]}"
      case "$s" in
          fan[0-9] | fan | pump)
              subcommand_index=$i
              is_fan=1
              break
              ;;
          led[0-9] | led | sync | ring | logo | external)
              subcommand_index=$i
              is_fan=0
              break
              ;;
      esac
      (( i++ ))
  done

  # check if it is a fan or an LED that is being set
  if [[ "$is_fan" -eq "1" ]]
  then
      _liquidctl_set_fan
  elif [[ "$is_fan" -eq "0" ]]
  then
      _liquidctl_set_led
  else

    # no trailing space here so that the fan number can be appended
    compopt -o nospace
    # possibly use some command here to get a list of all the possible channels from liquidctl
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -W "fan fan1 fan2 fan3 fan4 fan5 fan6 led led1 led2 led3 led4 led5 led6 pump sync ring logo external" -- "$cur"))
  fi
}

_liquidctl_set_fan ()
{
    COMPREPLY="speed"
}

_liquidctl_set_led ()
{
    COMPREPLY="color"
}


complete -F _liquidctl_main liquidctl


