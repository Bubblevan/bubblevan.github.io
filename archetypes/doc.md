---
schema: bubblevan/v1
id: doc-{{ replace (substr .Date 0 10) "-" "" }}
content_kind: doc
title: {{ replace .File.ContentBaseName "-" " " | title }}
date: {{ substr .Date 0 10 }}
updated: {{ substr .Date 0 10 }}
status: seed
visibility: public
summary:
topics: []
projects: []
aliases: []
review:
  last_reviewed: {{ substr .Date 0 10 }}
  next_review:
---

