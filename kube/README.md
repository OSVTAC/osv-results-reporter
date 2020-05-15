## Using ORR on Kubernetes

**Run the webserver**

```
kubectl create -f orr.yaml
```

**Use the proxy to visit**

```
```

## Debugging

**Get ORR logs**

```
kubectl logs $(kubectl get pod -l app=orr -o=jsonpath='{.items[0].metadata.name}') orr
```

### TODO

- Add a git puller to download data from git vs using sample data
