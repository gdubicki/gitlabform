#!/bin/bash

set -euo pipefail

# based on https://stackoverflow.com/a/28709668/2693875 and https://stackoverflow.com/a/23006365/2693875
cecho() {
  if [[ $TERM == "dumb" ]]; then
    echo $2
  else
    local color=$1
    local exp=$2
    if ! [[ $color =~ ^[0-9]$ ]] ; then
       case $(echo "$color" | tr '[:upper:]' '[:lower:]') in
        bk | black) color=0 ;;
        r | red) color=1 ;;
        g | green) color=2 ;;
        y | yellow) color=3 ;;
        b | blue) color=4 ;;
        m | magenta) color=5 ;;
        c | cyan) color=6 ;;
        w | white|*) color=7 ;; # white or invalid color
       esac
    fi
    tput setaf $color
    # shellcheck disable=SC2086
    echo $exp
    tput sgr0
  fi
}

script_directory="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
repo_root_directory="$script_directory/.."

if [[ $# == 1 ]] ; then
  gitlab_version="$1"
else
  gitlab_version="latest"
fi

cecho b "Pulling GitLab image version '$gitlab_version'..."
docker pull gitlab/gitlab-ee:$gitlab_version

cecho b "Preparing to start GitLab..."
existing_gitlab_container_id=$(docker ps -a -f "name=gitlab" --format "{{.ID}}")
if [[ -n $existing_gitlab_container_id ]] ; then
  cecho b "Stopping and removing existing GitLab container..."
  docker stop --time=30 "$existing_gitlab_container_id"
  docker rm "$existing_gitlab_container_id"
fi

gitlab_omnibus_config="gitlab_rails['initial_root_password'] = 'password'; registry['enable'] = false; grafana['enable'] = false; prometheus_monitoring['enable'] = false;"
if [[ -f Gitlab.gitlab-license || -n "${GITLAB_EE_LICENSE:-}" ]] ; then

  mkdir -p $repo_root_directory/config
  rm -rf $repo_root_directory/config/*

  if [[ -f Gitlab.gitlab-license ]]; then
    cecho b "EE license file found - using it..."
    cp Gitlab.gitlab-license $repo_root_directory/config/
  else
    cecho b "EE license env variable found - using it..."
    echo "$GITLAB_EE_LICENSE" | base64 -d > $repo_root_directory/config/Gitlab.gitlab-license
  fi

  gitlab_omnibus_config="$gitlab_omnibus_config gitlab_rails['initial_license_file'] = '/etc/gitlab/Gitlab.gitlab-license';"
  config_volume="--volume $repo_root_directory/config:/etc/gitlab"
else
  config_volume=""
fi

cecho b "Starting GitLab..."
# run GitLab with root password pre-set and as many unnecessary features disabled to speed up the startup
container_id=$(docker run --detach \
    --hostname gitlab.foobar.com \
    --env GITLAB_OMNIBUS_CONFIG="$gitlab_omnibus_config" \
    --publish 443:443 --publish 80:80 --publish 2022:22 \
    --name gitlab \
    --restart always \
    --volume "$repo_root_directory/dev/healthcheck-and-setup.sh:/healthcheck-and-setup.sh" \
    $config_volume \
    --health-cmd '/healthcheck-and-setup.sh' \
    --health-interval 2s \
    --health-timeout 2m \
    gitlab/gitlab-ee:$gitlab_version)

cecho b "Waiting 3 minutes before starting to check if GitLab has started..."
cecho b "(Run this in another terminal you want to follow the instance logs:"
cecho y "docker logs -f ${container_id}"
cecho b ")"
sleep 3m

$script_directory/await-healthy.sh

# create files with params needed by the tests to access GitLab
# (we are using these files to pass values from this script to the outside bash shell
# - we cannot change its env variables from inside it)
echo "http://localhost" > $repo_root_directory/gitlab_url.txt
echo "token-string-here123" > $repo_root_directory/gitlab_token.txt

cecho b 'Starting GitLab complete!'
echo ''
cecho b 'GitLab version:'
curl -H "Authorization:Bearer $(cat $repo_root_directory/gitlab_token.txt)" http://localhost/api/v4/version
echo ''
cecho b 'GitLab web UI URL (user: root, password: password)'
echo 'http://localhost'
echo ''
alias stop_gitlab='existing_gitlab_container_id=$(docker ps -a -f "name=gitlab" --format "{{.ID}}"); docker stop --time=30 $existing_gitlab_container_id ; docker rm $existing_gitlab_container_id'
cecho b 'Run this command to stop GitLab container:'
cecho r 'stop_gitlab'
echo ''
cecho b 'To start GitLab container again, re-run this script. Note that GitLab will NOT existing any data'
cecho b 'so the start will take a lot of time again. (But this is the only way to make GitLab in Docker stable.)'
echo ''
cecho b 'Run this to start the acceptance tests (it will automatically load GITLAB_URL from gitlab_url.txt'
cecho b 'and GITLAB_TOKEN from gitlab_token.txt created by this script):'
echo ''
cecho y 'pytest tests/acceptance'
