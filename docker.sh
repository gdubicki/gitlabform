#!/bin/bash
tags=""
version="$(cat version)"
for os in alpine debian
do
    effective_version="${os}_version"
    suffix="${os}${!effective_version}"
    latest="egnyte/gitlabform:latest-${suffix}"
    docker pull "${latest}" || echo "no cache is available"
    docker build \
        --build-arg PY_VERSION=$python_version \
        --build-arg OS_VERSION="${!effective_version}" \
        --file "${os}.Dockerfile" \
        --tag "${latest}" .
    tags="$tags ${latest}"

    docker tag "${latest}" "egnyte/gitlabform:${version}-${suffix}"
    tags="$tags egnyte/gitlabform:${version}-${suffix}"

    if [ "$os" = "alpine" ]
    then
        docker tag "${latest}" "egnyte/gitlabform:latest"
        tags="$tags egnyte/gitlabform:latest"
    fi
done

for image in $tags
do
    if [ ! -z "${PUSH_IMAGES}" ]
    then
            docker push $image
    else
        echo "$image"
    fi
done
