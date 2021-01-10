#!/bin/bash

set -euo pipefail

# based on https://stackoverflow.com/a/28709668/2693875 and https://stackoverflow.com/a/23006365/2693875
cecho() {
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
    echo $exp
    tput sgr0
}

cecho b "Pulling new GitLab image..."
docker pull gitlab/gitlab-ee:latest

cecho b "Preparing to start GitLab..."
existing_gitlab_container_id=$(docker ps -a -f "name=gitlab" --format "{{.ID}}")
if [[ -n $existing_gitlab_container_id ]] ; then
  cecho b "Stopping and removing existing GitLab container..."
  docker stop --time=30 "$existing_gitlab_container_id"
  docker rm "$existing_gitlab_container_id"
fi

mkdir -p config
if [[ -f company.gitlab-license ]] ; then
  cecho b "EE license file found - using it..."
  cp company.gitlab-license config/
fi
mkdir -p logs
mkdir -p data

cecho b "Starting GitLab..."
# run GitLab with root password pre-set and as many unnecessary features disabled to speed up the startup
docker run --detach \
    --hostname gitlab.foobar.com \
    --env GITLAB_OMNIBUS_CONFIG="gitlab_rails['initial_root_password'] = 'password'; registry['enable'] = false; grafana['enable'] = false; prometheus_monitoring['enable'] = false;" \
    --publish 443:443 --publish 80:80 --publish 2022:22 \
    --name gitlab \
    --restart always \
    --volume "$(pwd)/config:/etc/gitlab" \
    --volume "$(pwd)/logs:/var/log/gitlab" \
    --volume "$(pwd)/data:/var/opt/gitlab" \
    gitlab/gitlab-ee:latest

cecho b "Waiting 3 minutes before starting to check if GitLab has started..."
sleep 3m
until curl -X POST -s http://localhost/oauth/token | grep "Missing required parameter" >/dev/null ; do
  cecho b "Waiting 5 more secs for GitLab to start..." ;
  sleep 5s ;
done

# set variables used by the tests to access GitLab
export GITLAB_URL="http://localhost"

data='grant_type=password&username=root&password=password'
GITLAB_TOKEN=$(curl --data "${data}" -X POST -s "${GITLAB_URL}/oauth/token" | jq -r .access_token)
export GITLAB_TOKEN
cecho b 'Starting GitLab complete!. GITLAB_URL and GITLAB_TOKEN variables are set. You are ready to go!'

echo ''
cecho b 'GitLab version:'
curl -H "Authorization:Bearer $(cat gitlab_token.txt)" http://localhost/api/v4/version
echo ''
cecho b 'GitLab web UI URL (user: root, password: password)'
echo 'http://localhost'
echo ''
alias stop_gitlab='existing_gitlab_container_id=$(docker ps -a -f "name=gitlab" --format "{{.ID}}"); docker stop --time=30 $existing_gitlab_container_id ; docker rm $existing_gitlab_container_id'
cecho b 'Run "stop_gitlab" alias to stop the GitLab container.'
echo ''
cecho b 'To start GitLab container again, re-run this script. Note that GitLab will reuse existing ./data, ./config'
cecho b 'and ./logs dirs. To start new GitLab instance from scratch please delete them.'
echo ''
cecho b 'Run this to start the integration tests:'
echo ''
cecho y 'py.test gitlabform/gitlabform/test'
