# C2 SIP (laboratoire)

Prototype de commande et contrôle défensif utilisant des messages SIP sur UDP.
Il n'exécute pas de shell : seules les commandes `ping`, `info` et `time` sont acceptées.

```sh
export SIP_C2_SECRET='remplacez-moi-par-un-secret-long'
python3 server.py
# autre terminal
python3 agent.py --id labo-1
```

Dans le serveur : `list`, puis `send labo-1 ping`.

Le serveur écoute uniquement sur `127.0.0.1` par défaut. Pour un réseau de labo isolé,
utilisez explicitement `--bind 0.0.0.0` et configurez le pare-feu.
