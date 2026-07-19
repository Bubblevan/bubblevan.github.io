---
schema: bubblevan/v1
id: decision-{{ .File.ContentBaseName }}
content_kind: project_decision
title: {{ replace .File.ContentBaseName "-" " " | title }}
date: {{ substr .Date 0 10 }}
status: draft
visibility: public
projects: []
decision:
  status: proposed
  context:
  options: []
  choice:
  consequences: []
---

## Context

## Options Considered

## Decision

## Consequences
