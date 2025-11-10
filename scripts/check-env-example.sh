#!/bin/bash
echo ".env.example has changed!"
read -p "Have you updated production environment? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborting commit - please update production first"
    exit 1
fi
echo "Continuing with commit"