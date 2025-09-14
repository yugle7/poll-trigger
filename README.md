```bash
yc iam create-token
```

```bash
curl \
  --request POST \
  --url https://api.telegram.org/bot<токен_бота>/setWebhook \
  --header 'content-type: application/json' \
  --data '{"url": "https://<домен_API-шлюза>/fshtb-function"}'
```

```bash
curl \
  --request POST \
  --url https://api.telegram.org/bot<токен_бота>/deleteWebhook 
```