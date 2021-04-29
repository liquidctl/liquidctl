#!/usr/bin/env bash

# Bash completions for liquidctl.
#
# Requires bash-completion.[1]
#
# Users can place this file in the `completions` subdir of
# $BASH_COMPLETION_USER_DIR (defaults to `$XDG_DATA_HOME/bash-completion` or
# `~/.local/share/bash-completion` if $XDG_DATA_HOME is not set).
#
# Distros should instead use the directory returned by
#     pkg-config --variable=completionsdir bash-completion
#
# See [1] for more information.
#
# [1] https://github.com/scop/bash-completion
#
# Copyright (C) 2020-2020 Marshall Asch
# SPDX-License-Identifier: GPL-3.0-or-later

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
    liquidctl list | cut -d ':' -f 2 | sort -u | awk '{gsub(/\(|\)/,"",$0); print tolower($0)}'
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
    --json
    --version
    --help
    --single-12v-ocp
    --legacy-690lc
    --non-volatile
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
    --direction
    --start-led
    --maximum-leds
    --temperature-sensor
    "

    # generate options list and remove any flag that has already been given
    # note this will note remove the short and long versions
    options=($options_with_args $boolean_options)
    for i in "${!options[@]}";
    do
        if [[ "${COMP_WORDS[@]}" =~ "${options[i]}" ]]; then
            unset 'options[i]'
        fi
    done;
    options=$(echo "${options[@]}")



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
        --pump-mode)
            COMPREPLY=($(compgen -W "balanced quiet extreme" -- "$cur"))
            return
            ;;
        --* | -[a-z]*1)
            COMPREPLY=()
            return
            ;;
        esac

    # This will handle auto completing arguments even if they are given at the end of the command
    case "$cur" in
        -*)
            COMPREPLY=($(compgen -W "$options" -- "$cur"))
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

      COMPREPLY=($(compgen -W "$commands $options" -- "$cur"))
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
    local i=1 found=0

    # find the sub command (either a fan or an led to set)
    while [[ $i -lt $COMP_CWORD ]]; do
        local s="${COMP_WORDS[i]}"

        if [[ "$s" = "speed" ]]; then
            found=1
            break
        fi

        (( i++ ))
    done

    # check if it is a fan or an LED that is being set
    if [[ $found  =  1 ]]; then
        COMPREPLY=""
    else
        COMPREPLY="speed"
    fi
}

_liquidctl_set_led ()
{

    local i=1 found=0

    # find the sub command (either a fan or an led to set)
    while [[ $i -lt $COMP_CWORD ]]; do
        local s="${COMP_WORDS[i]}"
        if [[ "$s" = "color" ]]; then
            found=1
            break
        fi

        (( i++ ))
    done

    # check if it is a fan or an LED that is being set
    if [[ $found = 1 ]]; then
        COMPREPLY=""
    else
        COMPREPLY="color"
    fi

}

complete -F _liquidctl_main liquidctl
