#1. Create service file for docker
mkdir -p /etc/systemd/system/docker.service.d

#2. Create a proxy conf file for docker using "vi" editor and then Paste the lines below - save and exit.
vi /etc/systemd/system/docker.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=www-proxy.us.oracle.com:80" "HTTPS_PROXY=www-proxy.us.oracle.com:80" "NO_PROXY=localhost,127.0.0.1"


#3. Restart the daemon
systemctl daemon-reload

#4. Restart docker service
systemctl restart docker

#5. Check docker env variables
systemctl show --property=Environment docker

#6.Provide docker hub login-id and password.
docker login

#7.NOTE: Run the above command when in the same directory as asrvalidationscript. Ensure all required files are present.
#To build the docker images run:
docker build -t asrvu/ubuntu:`date +%F` -f ./dockerfile/asrvu_dockerfile .


