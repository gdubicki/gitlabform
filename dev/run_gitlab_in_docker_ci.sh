#!/bin/bash

# TODO: deduplicate the code by merging this and non "_ci" scripts together.
# TODO: they have been separated during migration to GitHub Actions, because using 'tput' in GHA
# TODO: resulted in "tput: No value for $TERM and no -T specified" error, even if we would set TERM="dumb" before

set -euo pipefail

# no tput at all
cecho() {
    local exp=$2
    echo "$exp"
}

cecho b "Starting GitLab..."

docker pull gitlab/gitlab-ee:latest

mkdir -p config
if [[ -f company.gitlab-license ]] ; then
  cecho b "EE license file found - using it..."
  cp company.gitlab-license config/
fi
mkdir -p logs
mkdir -p data

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
curl -H "Authorization:Bearer ${GITLAB_TOKEN}" http://localhost/api/v4/version
echo ''
