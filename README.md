# goat
simply the world's greatest discord bot.

## future plans
- make chat bot feature configurable per server, including: personality, history length, and inference model.
- add semantle group play support.
- add some sort of database to support saving state across restarts.
- detect conversational loops.
- improve goat personality text based on studying the openai docs, and reduce size if possible, because it is overhead on every request.
- keep stats per server and the ability to provide a daily quota (in tokens, or lines, not sure.)

## cost management
- the open ai queries are billed on a per-token basis.  token count per english request can be estimated by dividing the length by five.  the curie engine is $0.006/1k tokens, the davinci engine is $0.06/1k tokens
