---
schema: bubblevan/v1
id: project-{{ .File.ContentBaseName }}
content_kind: project
title: {{ replace .File.ContentBaseName "-" " " | title }}
date: {{ substr .Date 0 10 }}
updated: {{ substr .Date 0 10 }}
status: active
visibility: public
summary:
topics: []
aliases: []
project:
  role:
  stage: active
  highlights: []
  tech_stack: []
  repository:
  demo:
---

## Background

## Architecture

## Key Decisions
