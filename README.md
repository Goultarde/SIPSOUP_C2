# SIPSOUP

Prototype de commande et contrôle utilisant des messages SIP sur UDP.

```sh
export SIPSOUP_SECRET='remplacez-moi-par-un-secret-long'
python3 server.py
# autre terminal
python3 agent.py --id labo-1
```

Dans le serveur : `list`, puis `interact labo-1`. La session accepte `ping`,
`info`, `hostname`, `user`, `whoami`, `time`, `disk`, `bash <command>`, `help` et `back`.
`bash` sans argument ouvre une session persistante ; tapez `exit` pour la fermer.

Le serveur écoute uniquement sur `127.0.0.1` par défaut. Pour un réseau de labo isolé,
utilisez explicitement `--bind 0.0.0.0` et configurez le pare-feu.
