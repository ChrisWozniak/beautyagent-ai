{\rtf1\ansi\ansicpg1252\cocoartf2870
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\froman\fcharset0 Times-Roman;\f1\fmodern\fcharset0 Courier;\f2\froman\fcharset0 Times-Bold;
}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;\red109\green109\blue109;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;\cssrgb\c50196\c50196\c50196;}
\margl1440\margr1440\vieww28860\viewh15600\viewkind0
\deftab720
\pard\pardeftab720\sa240\partightenfactor0

\f0\fs24 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 for all three channels (
\f1\fs26 tiktok
\f0\fs24 , 
\f1\fs26 instagram
\f0\fs24 , 
\f1\fs26 email
\f0\fs24 ) showing one channel 
\f1\fs26 completed
\f0\fs24  + PASSED, one 
\f1\fs26 completed
\f0\fs24  + FAILED, and one 
\f1\fs26 error
\f0\fs24 , all in one response.\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 What changed:
\f0\b0  
\f1\fs26 api_contract.md
\f0\fs24  now has 5 example payloads instead of 4.\

\f2\b Rationale:
\f0\b0  None of the original four payloads exercised more than one channel per request, so the partial-results dashboard was only ever discussed in the abstract. A real example gives Chris something concrete to build the concurrent per-channel loop against, and gives the frontend a real case to test the partial-results card layout before Day 3.\
\pard\pardeftab720\partightenfactor0
\cf3 \strokec3 \
\pard\pardeftab720\sa298\partightenfactor0

\f2\b\fs36 \cf0 \strokec2 5. Channel drafting approach\
\pard\pardeftab720\sa240\partightenfactor0

\fs24 \cf0 Decision:
\f0\b0  Option B \'97 independent draft \uc0\u8594  audit \u8594  revise loop per channel, run concurrently rather than sequentially.\

\f2\b What changed:
\f0\b0  This was previously framed as a recommendation in 
\f1\fs26 api_contract.md
\f0\fs24 's Backend Notes, not a locked decision. Now confirmed and stated as decided.\

\f2\b Rationale:
\f0\b0  The response schema already assumes this structure \'97 each result object carries its own 
\f1\fs26 retry_exhausted
\f0\fs24  and 
\f1\fs26 detection_source
\f0\fs24 , which only makes sense if channels can pass, fail, and retry independently. Running the three loops concurrently (rather than sequentially) is also likely necessary to hit the PRD's 
\f1\fs26 <3s
\f0\fs24  response-time target.\
}