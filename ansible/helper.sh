#!/usr/bin/env bash
echo "Ip?"
read ip_ans
ansible-playbook -i "$ip_ans", -u debuser --ask-vault-pass --ask-pass --ask-become-pass ansible/docker.yaml 