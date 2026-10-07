#!/bin/bash

sudo apt install python3.12-venv unzip zip clang-15 lld-15
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install patcherex2