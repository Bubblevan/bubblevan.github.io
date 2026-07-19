---
schema: bubblevan/v1
id: daily-{{ replace (substr .Date 0 10) "-" "" }}
content_kind: daily
title: {{ substr .Date 5 5 }}
date: {{ substr .Date 0 10 }}
status: published
visibility: public
summary:
topics: []
projects: []
---

## Log

## Links

## Tasks

## Events

## Project Notes
