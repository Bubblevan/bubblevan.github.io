---
schema: bubblevan/v1
id: blog-{{ replace (substr .Date 0 10) "-" "" }}
content_kind: blog
title: {{ replace .File.ContentBaseName "-" " " | title }}
date: {{ substr .Date 0 10 }}
updated: {{ substr .Date 0 10 }}
status: draft
visibility: public
summary:
topics: []
projects: []
aliases: []
---

