[< cli-eaa documentation](../../README.md)

# akamai eaa certificate

Alias: `cert`

## Display certificates

The command `cert` displays all the certificate you have configured in EAA, along with the CN and SAN attributes in the `hosts` field, as a `+` separated list.

Example with a wildcard certificate:

```
$ akamai eaa cert | head -n1
#Certificate-ID,cn,type,expiration,days left,hosts
crt://●●●●●●●●●●●●●●●●●●●●●●,*.akamaidemo.net,Custom,2031-06-05T22:56:34,3307,*.akamaidemo.net+akamaidemo.net
```

## Rotate certificates

The cli-eaa helps with this task with the `akamai eaa certificate` command. 

Pass the certificate and key file as parameter with the optional passphrase to replace the existing certificate.
By default, the rotation does NOT redeploy the impacted application or IdP. 
To trigger the re-deployment of all impacted applications and IdP, add the ``--deployafter`` flag.

```
$ akamai eaa certificate crt://certificate-UUID rotate --key ~/certs/mycert.key --cert ~/certs/mycert.cert --deployafter
Rotating certificate certificate-UUID...
Certificate CN: *.akamaidemo.net (*.akamaidemo.net Lets Encrypt)
Certificate certificate-UUID updated, 3 application/IdP(s) have been marked ready for deployment.
Deploying application Multi-origin Active-Active Demo (US-East) (app://appid-1)...
Deploying application Multi-origin Active-Active Demo (US-West) (app://appid-2)...
Deploying IdP Bogus IdP to test EME-365 (idp://idpid-1)...
Deployment(s) in progress, it typically take 3 to 5 minutes
Use 'akamai eaa cert crt://certificate-UUID status' to monitor the progress.
```

Check the deployment status:

```bash
$ akamai eaa cert crt://certificate-UUID status
#App/IdP ID,name,status
app://appid-1,Multi-origin Active-Active Demo (US-East),Pending
app://appid-2,Multi-origin Active-Active Demo (US-West),Pending
idp://idpid-1,Bogus IdP to test EME-365,Pending
```