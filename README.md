# C2 SIP (laboratoire)

Prototype de commande et contrôle défensif utilisant des messages SIP sur UDP.
Il n'exécute pas de shell : seules les commandes de diagnostic intégrées sont acceptées.

```sh
export SIP_C2_SECRET='remplacez-moi-par-un-secret-long'
python3 server.py
# autre terminal
python3 agent.py --id labo-1
```

Dans le serveur : `list`, puis `interact labo-1`. La session accepte `ping`,
`info`, `hostname`, `user`, `time`, `disk`, `help` et `back`.

Le serveur écoute uniquement sur `127.0.0.1` par défaut. Pour un réseau de labo isolé,
utilisez explicitement `--bind 0.0.0.0` et configurez le pare-feu.
