# Nova Messenger — Render v1

Первый серверный MVP:
- регистрация и вход;
- JWT-подобные сессии для MVP;
- WebSocket;
- обмен сообщениями между одновременно подключёнными пользователями;
- мобильный интерфейс;
- FastAPI.

Важно: пользователи и сообщения пока хранятся в памяти процесса. На бесплатном Render это не постоянное хранилище. Следующий этап — PostgreSQL, нормальные JWT, таблицы чатов/сообщений, загрузка файлов, push и WebRTC.

## Render
Можно подключить GitHub-репозиторий и создать Web Service.
Build: `pip install -r requirements.txt`
Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
