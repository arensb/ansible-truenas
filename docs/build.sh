#!/usr/bin/env bash
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

pushd "$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
trap "{ popd; }" EXIT

ANSIBLE_COLLECTIONS_PATH=..
export ANSIBLE_COLLECTIONS_PATH

# Create collection documentation into temporary directory
rm -rf temp-rst
mkdir -p temp-rst
chmod og-w temp-rst  # antsibull-docs wants that directory only readable by itself

antsibull-changelog generate
mv ../CHANGELOG.rst temp-rst

antsibull-docs \
    --config-file antsibull-docs.cfg \
    collection \
    --use-current \
    --squash-hierarchy \
    --dest-dir temp-rst \
    arensb.truenas

# Copy collection documentation into source directory
rsync -cprv --delete-after temp-rst/ rst/

# Build Sphinx site
sphinx-build -M html rst build -c . -W --keep-going

