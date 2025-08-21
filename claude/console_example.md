INFO:main:================================================================================
INFO:main:NEW CHAT REQUEST RECEIVED
INFO:main:================================================================================
INFO:main:USER QUESTION: Hey Matt, what do you think of Meetup?
INFO:main:API KEY (truncated): sk-or-v1-69783887411...
INFO:main:MODEL: anthropic/claude-3.5-sonnet
INFO:main:================================================================================
2025/08/20 23:01:15 WARNING dspy.primitives.module: Calling module.forward(...) on MattGPT directly is discouraged. Please use module(...) instead.
INFO:matt_gpt:Processing question: Hey Matt, what do you think of Meetup?...
INFO:retrievers:Retrieving context for query: Hey Matt, what do you think of Meetup?...
INFO:llm_client:Initializing OpenRouter client...
INFO:llm_client:Using environment OpenRouter API key
INFO:llm_client:OpenRouter client initialized successfully
INFO:retrievers:Retrieved 10 message contexts
INFO:retrievers:============================================================
INFO:retrievers:RAG MESSAGE RETRIEVAL DETAILS:
INFO:retrievers:============================================================
INFO:retrievers:MESSAGE 1:
INFO:retrievers: Content: [2024-05-05 19:54:35.070000] Hey Matt - Hope you're having a good weekend!

I wanted to check in and see if you thought you'd be coming back to either...
INFO:retrievers: (truncated from 182 chars)
INFO:retrievers:------------------------------
INFO:retrievers:MESSAGE 2:
INFO:retrievers: Content: [2024-08-15 21:30:17.590000] Did you know Andrew Rubner from high school? (My grade)...
INFO:retrievers:------------------------------
INFO:retrievers:MESSAGE 3:
INFO:retrievers: Content: [2024-08-15 21:30:57.921000] He transferred and was super weird but also confident, I was somewhat friends with him...
INFO:retrievers:------------------------------
INFO:retrievers:MESSAGE 4:
INFO:retrievers: Content: [2024-08-15 21:31:09.824000] I think he would be a good fit for your meetup...
INFO:retrievers:------------------------------
INFO:retrievers:MESSAGE 5:
INFO:retrievers: Content: [2024-05-16 22:01:20.901000] Hey Matt - Meeting still on for tonight?...
INFO:retrievers:------------------------------
INFO:retrievers:... and 5 more messages
INFO:retrievers:============================================================
INFO:retrievers:Retrieved 0 personality documents
INFO:retrievers:============================================================
INFO:retrievers:RAG PERSONALITY DOCS DETAILS:
INFO:retrievers:============================================================
INFO:retrievers:============================================================
INFO:retrievers:Total context items retrieved: 10
INFO:matt_gpt:Retrieved 10 context passages
INFO:matt_gpt:============================================================
INFO:matt_gpt:RAG RETRIEVAL RESULTS:
INFO:matt_gpt:============================================================
INFO:matt_gpt:PASSAGE 1:
INFO:matt_gpt: Content: [2024-05-05 19:54:35.070000] Hey Matt - Hope you're having a good weekend!

I wanted to check in and see if you thought you'd be coming back to either (or both) of the next meet-ups?...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 2:
INFO:matt_gpt: Content: [2024-08-15 21:30:17.590000] Did you know Andrew Rubner from high school? (My grade)...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 3:
INFO:matt_gpt: Content: [2024-08-15 21:30:57.921000] He transferred and was super weird but also confident, I was somewhat friends with him...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 4:
INFO:matt_gpt: Content: [2024-08-15 21:31:09.824000] I think he would be a good fit for your meetup...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 5:
INFO:matt_gpt: Content: [2024-05-16 22:01:20.901000] Hey Matt - Meeting still on for tonight?...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 6:
INFO:matt_gpt: Content: [2024-05-11 23:26:21.174000] Hey Matt - How'd the meet-up turn out?

Also, there's an improv show on May 31st in Madison (at the community center) that some members of the group are planning to go to....
INFO:matt_gpt: (truncated from 428 chars)
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 7:
INFO:matt_gpt: Content: [2024-05-11 23:26:21.174000] Hey Matt - How'd the meet-up turn out?

Also, there's an improv show on May 31st in Madison (at the community center) that some members of the group are planning to go to....
INFO:matt_gpt: (truncated from 428 chars)
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 8:
INFO:matt_gpt: Content: [2024-04-20 14:17:43.883000] Hi Matt, have you decided?...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 9:
INFO:matt_gpt: Content: [2024-04-20 14:17:43.883000] Hi Matt, have you decided?...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:PASSAGE 10:
INFO:matt_gpt: Content: [2025-01-23 23:30:18.276000] Hi Matt! This is Karin from the ifs meet up. How are you and Sarah doing? We are interested in your gathering. Did you set a date?...
INFO:matt_gpt:----------------------------------------
INFO:matt_gpt:============================================================
INFO:matt_gpt:Using user-provided OpenRouter API key for generation
INFO:llm_client:Initializing OpenRouter client...
INFO:llm_client:Using user-provided OpenRouter API key
INFO:llm_client:OpenRouter client initialized successfully
INFO:matt_gpt:============================================================
INFO:matt_gpt:RAW PROMPT INPUT (User OpenRouter Key):
INFO:matt_gpt:============================================================
INFO:matt_gpt:FULL PROMPT:
You are Matt, responding authentically based on your communication style and experiences.

Context from Matt's messages and personality:
[2024-05-05 19:54:35.070000] Hey Matt - Hope you're having a good weekend!

I wanted to check in and see if you thought you'd be coming back to either (or both) of the next meet-ups?

[2024-08-15 21:30:17.590000] Did you know Andrew Rubner from high school? (My grade)

[2024-08-15 21:30:57.921000] He transferred and was super weird but also confident, I was somewhat friends with him

[2024-08-15 21:31:09.824000] I think he would be a good fit for your meetup

[2024-05-16 22:01:20.901000] Hey Matt - Meeting still on for tonight?

[2024-05-11 23:26:21.174000] Hey Matt - How'd the meet-up turn out?

Also, there's an improv show on May 31st in Madison (at the community center) that some members of the group are planning to go to. It'd be an 8pm - 9:30pm show. Short form improv by a group called the Flip Side - all very experienced improvisers. Should be a great show.

If you think you'd be interested in being part of the group outing to it, let me know!

[2024-05-11 23:26:21.174000] Hey Matt - How'd the meet-up turn out?

Also, there's an improv show on May 31st in Madison (at the community center) that some members of the group are planning to go to. It'd be an 8pm - 9:30pm show. Short form improv by a group called the Flip Side - all very experienced improvisers. Should be a great show.

If you think you'd be interested in being part of the group outing to it, let me know!

[2024-04-20 14:17:43.883000] Hi Matt, have you decided?

[2024-04-20 14:17:43.883000] Hi Matt, have you decided?

[2025-01-23 23:30:18.276000] Hi Matt! This is Karin from the ifs meet up. How are you and Sarah doing? We are interested in your gathering. Did you set a date?

User question: Hey Matt, what do you think of Meetup?

Respond as Matt would, using his voice and communication style:
