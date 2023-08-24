#!/usr/bin/env bash
echo "Ip?"
read ip_ans
echo "User?"
read user_ans
ansible-playbook -i "$ip_ans", -u "$user_ans" --ask-vault-pass --ask-pass --ask-become-pass docker.yaml 