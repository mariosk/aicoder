#!/bin/bash

BUMPVERSION_CFG=bumpversion.cfg

function runme() {
    python3 $1 $2
}

function update_git_commit_hash() {
    commit_hash=$(git rev-parse HEAD)
    commit_hash_short=$(git rev-parse --short HEAD)
    echo "Current commit hash: $commit_hash"
    tag=$(git tag --contains $commit_hash)
    if [ "$tag" != "" ]; then
        echo "Commit $commit_hash is tagged with: $tag"
    else
        echo "Commit $commit_hash is not tagged with any tag"
        current_version=$(grep -oP '(?<=current_version = ).*' ${BUMPVERSION_CFG})
        sed -i "s/current_version = $current_version/current_version = $commit_hash_short/" ${BUMPVERSION_CFG}
        cat ${BUMPVERSION_CFG}
    fi
}
