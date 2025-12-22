---
id: example-highlight-blocks
title: 高亮块组件使用示例
sidebar_label: 高亮块示例
---

import DocumentMetadata from '@site/src/components/DocumentMetadata';
import { 
  InfoBlock, 
  WarningBlock, 
  SuccessBlock, 
  ErrorBlock, 
  NoteBlock, 
  TipBlock, 
  QuestionBlock 
} from '@site/src/components/HighlightBlock';
import CollapsibleBlock from '@site/src/components/CollapsibleBlock';

# 高亮块组件使用示例

<DocumentMetadata />

这个页面展示了各种高亮块组件的使用方法，这些组件类似于飞书文档中的信息框，可以让内容更加醒目和美观。

## 信息块 (InfoBlock)

<InfoBlock title="重要信息">
  这是一个信息块，用于展示重要的信息内容。你可以在这里放置任何需要强调的文本内容。
</InfoBlock>

## 警告块 (WarningBlock)

<WarningBlock title="注意事项">
  这是一个警告块，用于提醒用户注意某些重要事项。通常用于安全提示、注意事项等。
</WarningBlock>

## 成功块 (SuccessBlock)

<SuccessBlock title="操作成功">
  这是一个成功块，用于展示操作成功的信息。通常用于确认操作完成、显示成功状态等。
</SuccessBlock>

## 错误块 (ErrorBlock)

<ErrorBlock title="错误提示">
  这是一个错误块，用于展示错误信息或问题。通常用于显示错误状态、问题描述等。
</ErrorBlock>

## 笔记块 (NoteBlock)

<NoteBlock title="学习笔记">
  这是一个笔记块，用于记录学习过程中的重要笔记。你可以在这里记录关键概念、公式、代码片段等。
</NoteBlock>

## 提示块 (TipBlock)

<TipBlock title="实用技巧">
  这是一个提示块，用于分享实用的技巧和建议。通常用于提供最佳实践、优化建议等。
</TipBlock>

## 问题块 (QuestionBlock)

<QuestionBlock title="常见问题">
  这是一个问题块，用于展示常见问题或疑问。通常用于FAQ、问题解答等场景。
</QuestionBlock>

## 可展开块 (CollapsibleBlock)

<CollapsibleBlock title="点击展开查看详细内容" icon="?">
  这是一个可展开的高亮块，点击右上角的^按钮可以展开或隐藏内容。非常适合放置一些详细但不需要一直显示的信息。
  
  ### 使用场景
  - 详细的配置说明
  - 扩展的代码示例
  - 可选的补充信息
  - 折叠的长列表
  
  ### 特点
  - 支持自定义图标
  - 平滑的展开/隐藏动画
  - 响应式设计
  - 深色主题适配
</CollapsibleBlock>

<CollapsibleBlock title="默认展开的内容" icon="?" defaultExpanded={true}>
  这个可展开块默认是展开状态的，适合放置一些重要但可能比较长的内容。
  
  **默认展开**：通过设置 `defaultExpanded={true}` 可以让内容默认显示。
  
  **交互体验**：用户可以点击^按钮来隐藏内容，再次点击可以重新展开。
</CollapsibleBlock>

## 自定义图标

你还可以自定义图标：

<InfoBlock title="自定义图标" icon="?">
  这个信息块使用了自定义的火箭图标，而不是默认的信息图标。
</InfoBlock>

<WarningBlock title="自定义警告" icon="?">
  这个警告块使用了火焰图标，更加醒目。
</WarningBlock>

<CollapsibleBlock title="自定义图标" icon="?">
  可展开块也支持自定义图标，让内容更加生动有趣。
</CollapsibleBlock>

## 代码示例

以下是如何在Markdown中使用这些组件的代码：

```jsx
import { InfoBlock, WarningBlock, SuccessBlock } from '@site/src/components/HighlightBlock';
import CollapsibleBlock from '@site/src/components/CollapsibleBlock';

// 基本用法
<InfoBlock title="标题">
  内容
</InfoBlock>

// 自定义图标
<WarningBlock title="警告" icon="?">
  警告内容
</WarningBlock>

// 无标题
<SuccessBlock>
  成功信息
</SuccessBlock>

// 可展开块
<CollapsibleBlock title="可展开内容" icon="?">
  详细内容
</CollapsibleBlock>

// 默认展开
<CollapsibleBlock title="默认展开" defaultExpanded={true}>
  默认显示的内容
</CollapsibleBlock>
```

## 使用建议

1. **选择合适的类型**：根据内容性质选择合适的高亮块类型
2. **保持简洁**：标题和内容要简洁明了
3. **适度使用**：不要过度使用，以免影响阅读体验
4. **图标选择**：可以使用emoji或自定义图标来增强视觉效果
5. **可展开块**：适合放置详细但不需要一直显示的信息

这些高亮块组件可以让你的文档更加生动有趣，提高用户的阅读体验！
