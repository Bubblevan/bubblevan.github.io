---
schema: bubblevan/v1
id: retro-{{ .File.ContentBaseName }}
content_kind: retrospective
title: {{ replace .File.ContentBaseName "-" " " | title }}
date: {{ substr .Date 0 10 }}
status: draft
visibility: public
projects: []
retro:
  situation:
  task:
  action:
  result:
  evidence: []
  lessons: []
---

## Situation

## Task

## Action

## Result

## Lessons Learned
