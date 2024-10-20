
rm -r /tmp/server
mkdir -p /tmp/server/cml
cp -r ../server/* /tmp/server/cml/
rm -r /tmp/server/cml/data/*
rm -r /tmp/server/cml/.htaccess
mkdir /tmp/server/cml/webpage/downloads
tar -czvf /tmp/server/cml/webpage/downloads/client.tar.gz ../app


