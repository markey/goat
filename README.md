# goat
simply the world's greatest discord bot.

## future plans
- make chat bot feature configurable per server, including: personality, history length, and inference model.
- keep stats per server and the ability to provide a daily quota (in tokens, or lines, not sure.)
- add semantle group play support.
- add data persistence layer to save state across restarts.
- detect conversational loops and defuse them.
- tune goat personality text, there is a lot of advice in the openai docs.
- reduce size of goat personality text; this represents >90% of our cost to run goat.
- make goat understand @mentions of other users.

## cost management
- the open ai queries are billed on a per-token basis.  token count per english request can be estimated by dividing the length by four.  the curie engine is $0.006/1k tokens, the davinci engine is $0.06/1k tokens
