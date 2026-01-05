# WorldVLA: Towards Autoregressive Action World Model

我发现直接在豆包浏览器里面打开类似下面的Arxiv链接，就不用费事八荒的下下来再拖给豆包了，这是一种加速我略读文献的方法！

https://arxiv.org/pdf/2506.21539

![](/paper/worldvla-overview.png)

为了解决视觉-语言-动作（VLA）模型和世界模型中固有的限制，我们提出了WorldVLA，这是一种用于统一动作与图像理解和生成的自回归动作世界模型。如图1所示，WorldVLA采用三个独立的分词器对图像、文本和动作进行编码。来自不同模态的标记被设置为共享相同的词汇表，这样在这些模态间的理解和生成就可以在单一的大型语言模型（LLM）架构中实现统一。世界模型部分通过基于输入动作生成视觉表征来捕捉环境的潜在物理动态。这种动作解读和环境物理学习的过程对于在动作模型中实现有效的决策制定至关重要。同时，嵌入在其中的动作模型改进了对视觉数据的理解，从而提高了世界模型执行图像生成的精度。这种双向增强造就了一个更强大、更全面的模型，该模型既能够理解动作和图像，也能够生成动作和图像。

| Model Type | Discrete | Continous | Input | Output |
| --- | --- | --- | --- | --- |
| Action Model | OpenVLA ( Kim et al. , 2024 ) | π 0 ( Black et al. , 2024 ) | T + V | A |
| Video Prediction Model | MAGVIT ( Yu et al. , 2023 ) | SVD ( Blattmann et al. , 2023 ) | T + V | V |
| World Model | iVideoGPT ( Wu et al. , 2025 ) | DWS ( He et al. , 2025 ) | T + V + A | V |
| Action World Model | WorldVLA (ours) | UVA ( Li et al. , 2025 ) | T + V + A | V + A |

![](/paper/worldvla-architect.png)
