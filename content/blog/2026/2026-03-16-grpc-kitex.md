---
date: 2026-03-16
title: 远程过程调用 RPC
authors: [bubblevan]
tags: []
---
## 先把词分开
HTTP 本质上是一个**应用层通信协议**。浏览器和服务器、客户端和服务端，就是靠 HTTP request / response 交换消息；HTTP 定义了方法、状态码、头、语义这些东西。RFC 9110 直接把 HTTP 定义为“**无状态的应用层协议**”，MDN 也把 HTTP 描述为 Web 上**数据交换**的基础客户端—服务器协议。
在此基础上，REST 定义为一种**架构**风格，它强调资源（resource）、统一接口（uniform interface）等约束。
```
GET /users/123
POST /orders
DELETE /comments/9
```
典型REST风格不是在调用函数名，而是在对一个资源做操作。

而 RPC（Remote Procedure Call，远程过程调用） 的核心思想很简单：客户端可以像调用本地对象的方法一样，去调用另一台机器上的服务方法；服务端实现这个接口，客户端通过生成的代码去调用它。

打个比方：让另一台服务器上的程序帮你计算“1+1”。
- 如果没有RPC，你需要自己组一个HTTP请求、把数据转成JSON、处理网络异常……非常麻烦。
- 而有了RPC，你只需要在代码里写一句 `result = add(1, 1)`，剩下的**网络通信、数据打包、错误处理**都由RPC框架帮你搞定！
- 其让分布式系统的开发变得简单直观

也就是说，HTTP 是传输层面的协议选择，REST / RPC 是接口设计风格。gRPC 允许客户端直接调用远程机器上的方法，默认使用 Protocol Buffers 作为 IDL 和消息格式；它的核心调用模型是 RPC。与此同时，gRPC 的实现又是建立在 HTTP/2 之上的。

## RPC 是什么
我以前主要做前后端项目，对“调用接口”这件事的直觉大多来自：
- 浏览器发请求
- 前端调后端接口
- 后端暴露一个 URL
- 数据通常是 JSON

这套经验没有错，但我目前为止都默认认为**远程调用 = 发 HTTP 请求 = 调一个 URL**；
而 RPC 想建立的是另一种直觉是**远程调用 = 调一个不在本进程里的函数**

这个“像函数一样调用远程服务”的感觉，就是 RPC 的核心。gRPC 官方把 RPC 解释成：客户端可以像调用本地对象的方法一样，去调用另一台机器上的方法；服务接口由定义文件描述，再生成客户端和服务端代码。gRPC 还可以把 Protocol Buffers 同时用作接口定义语言和消息交换格式。

```go
package main

import "fmt"

func SayHello(name string) string {
	return "Hello, " + name
}

func main() {
	msg := SayHello("Bubble")
	fmt.Println(msg)
}
```
我们假装`SayHello`不在当前进程里，它在另一台机器的一个服务里，客户端只能通过网络去调用它，那最小模型至少要有：
- 服务名
- 方法名
- 请求参数
- 响应结果
### Server示例
```go
package main
import (
  "bufio"
  "encoding/json"
  "fmt"
  "net"
)
// type是定义新类型的关键字，这里定义了结构体类型
// 结构体字段后的 `json:"service"` 等是结构体标签（struct tag）用于指定 JSON 序列化/反序列化时的字段名称
type RPCRequest struct {
  Service string          `json:"service"`
  Method  string          `json:"method"`
  Payload json.RawMessage `json:"payload"`
}
// RawMessage保存原始JSON数据，延迟解析

type RPCResponse struct {
  OK  bool  `json:"ok"`
  Data interface{} `json:"data,omitempty"`  // internface{}可以存放任意类型
  Error string `json:"error,omitempty"`     // omitempty表示如果为空则省略该字段
}

// 请求参数结构
type HelloRequest struct {
  Name string `json:"name"`
}
// 响应数据结构
type HelloReply struct {
  Message string `json:"message"`
}

// 业务函数
func sayHello(req HelloRequest) HelloReply {
  // 创建并返回HelloReply实例，字段名：值 语法
  return HelloReply{
    Message: "Hello, " + req.Name,
  }
}

// 处理单个客户端连接
// 参数conn是net.Conn接口，代表一个网络连接
func handleConn(conn net.Conn) {
  // defer用于注册一个函数调用，在包含它的函数前执行，确保连接最终被关闭避免资源泄露
  defer conn.Close()

  // 创建一个带缓冲的读取器，从连接中读取数据
  reader := bufio.NewReader(conn)
  // ReadBytes读取直到遇到指定的分隔符换行符，返回包含分隔符的字符切片
  line, err := reader.ReadBytes('\n')
  if err != nil {
    return
  }
  // 声明Req变量用于存放解析后的请求
  var req RPCRequest
  // 声明一个新变量err并赋值为json.Unmarshal的返回值，后面的条件表达式为True则执行
  if err := json.Unmarshal(line, &req); err != nil {
    resp := RPCResponse{OK: false, Error: "bad request json"}
    // json.Marshal将结构体转为JSON字节数据，err被忽略（生产环境一般需要处理）
    b, _ := json.Marshal(resp)
    conn.Write(append(b, '\n'))
    return
  }

  // 服务路由 & 方法分发：根据Service和Methods调用对应函数
  if req.Service == "GreeterService" && req.Method == "SayHello" {
    var helloReq HelloRequest
    // 解析Payload字段到HelloRequest结构体
    if err := json.Unmarshal(req.Payload, &helloreq); err != nil {
      resp := RPCResponse{OK: false, Error: "Bad Payload"}
      b, _ := json.Marshal(resp)
      conn.Write(append(b, '\n'))
      return
    }

    // 调用业务函数获得回复
    reply := sayHello(helloReq)
    // 包装成功响应回复客户端，Data字段赋值为relpy
    resp := RPCResponse{OK: true, Data: reply}
    b, _ := json.Marshal(resp)
    conn.Write(append(b, '\n'))
    return
  }

  // 如果服务方法不匹配返回错误
  resp := RPCResponse{OK: false, Error: "unknown service/method"}
  b, _ := json.Marshal(resp)
  conn.Write(append(b, '\n'))
}

func main() {
  // net.Listen 在指定网络和地址上创建监听器
  ln, err := net.Listen("tcp", "9000")
  if err != nil {
    panic(err)
  }
  fmt.Println("RPC server listening on 9000")

  // 无限循环，持续接受新连接
  for {
    // Accept 阻塞直到收到一个连接请求，返回连接对象
    conn, err := ln.Accept()
    if err != nil {
      continue      // 如果接受连接失败（例如监听器被关闭），则跳过继续等待下一个连接
    }
    // go 关键字启动一个 goroutine（轻量级线程）并发处理连接
    // handleConn 会在新的 goroutine 中运行，不会阻塞主循环接受更多连接
    go handleConn(conn)
  }
}
```
#### Go语法小知识1
- 字段名是 Go 内部使用的（比如 req.Service 访问字段）。但当你把 Go 数据转换成 JSON（序列化）时，Go 默认会把字段名原样输出为 JSON 的键名（比如 Service 变成 "Service"）。但通常 JSON 里习惯用小写开头的键（比如 "service"），这时候就需要用标签来指定映射关系。
- 标签的作用：它告诉 Go 的 JSON 编解码器（encoding/json 包）在序列化或反序列化时，应该用哪个名字作为 JSON 的键。比如 json:"service" 表示：当把 Service 字段转成 JSON 时，使用 "service" 作为键名；反过来，从 JSON 解析时，也把键名为 "service" 的值赋给 Service 字段。
- 选项 omitempty：标签里还可以加选项，比如 json:"data,omitempty" 表示如果 Data 字段是零值（空、0、false、nil 等），那么在生成的 JSON 中就省略这个字段，不输出。
- 所以，字段名和标签是两码事：字段名是 Go 代码里用的，标签是给 JSON 编解码器看的。
- `:=` 是一个**短变量声明**（short variable declaration）操作符，用于**声明**并**初始化**一个新变量，同时让 Go 自动推断该变量的类型
- 相当于var声明的简介形式，`var x int = 10` 可以写成 `x := 10`
- `=` 只能用于给已声明的变量赋值，不能用于声明新变量

> `.go` 源文件需要经过编译器处理，生成一个可执行二进制文件才能运行；
> Python、JavaScript 这类解释型语言不需要提前编译，直接由解释器运行源代码

### Client示例
```go
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
)

type RPCRequest struct {
	Service string      `json:"service"`
	Method  string      `json:"method"`
	Payload interface{} `json:"payload"`
}

type RPCResponse struct {
	OK    bool            `json:"ok"`
	Data  json.RawMessage `json:"data"`
	Error string          `json:"error"`
}

type HelloRequest struct {
	Name string `json:"name"`
}

type HelloReply struct {
	Message string `json:"message"`
}

func main() {
	conn, err := net.Dial("tcp", "127.0.0.1:9000")
	if err != nil {
		panic(err)
	}
	defer conn.Close()

	req := RPCRequest{
		Service: "GreeterService",
		Method:  "SayHello",
		Payload: HelloRequest{Name: "Bubble"},
	}

	b, _ := json.Marshal(req)
	conn.Write(append(b, '\n'))

	reader := bufio.NewReader(conn)
	line, err := reader.ReadBytes('\n')
	if err != nil {
		panic(err)
	}

	var resp RPCResponse
	if err := json.Unmarshal(line, &resp); err != nil {
		panic(err)
	}

	if !resp.OK {
		panic(resp.Error)
	}

	var reply HelloReply
	if err := json.Unmarshal(resp.Data, &reply); err != nil {
		panic(err)
	}

	fmt.Println(reply.Message)
}
```

- **客户端**：没有调用 URL，而是把 `服务名.GreeterService、方法名.SayHello、参数{Name:"Bubble"}` 这三个东西打包成一个 JSON 结构，通过 TCP 发送给服务器。
- **服务端**：不是在匹配 /hello 这样的路由，而是在做“服务 + 方法”的分发。监听 TCP 端口，收到 JSON 后，解析出服务名和方法名，找到对应的本地函数 sayHello，把参数传进去执行，再把结果打包成 JSON 返回给客户端。

这就是 RPC 最原始的感觉。
### Protobuf
上面那份 JSON 协议，其实已经隐含了一份“契约”：
- 有 GreeterService
- 有 SayHello
- SayHello 吃 HelloRequest
- SayHello 返回 HelloReply

手写的 JSON 协议虽然能工作，但有三个问题：
- 松散、容易出错：字段名写错、类型不匹配，只能在运行时发现。
- 效率低：JSON 是文本，体积大，解析慢。
- 没有代码生成：每次都要自己写打包解包代码，很繁琐。

`.proto`这种**接口定义语言**（IDL）就是为了解决这些问题诞生的，专门用来**严格地描述服务和方法，以及请求和响应的结构**。
| 对比维度       | 普通 JSON 接口文档                     | .proto                                  |
|----------------|----------------------------------------|-----------------------------------------|
| 可读性         | 人看得懂                               | 人能看                                  |
| 机器适配性     | 机器不一定能直接用来生成调用代码       | 机器能直接生成代码                      |
| 类型约束       | 类型约束比较松                         | 字段类型和字段编号明确                  |
| 演进规范       | 演进规范常常靠约定                     | 天生考虑兼容演进                        |

```proto
syntax = "proto3";

package hello;

service GreeterService {
  rpc SayHello(HelloRequest) returns (HelloReply);
}

message HelloRequest {
  string name = 1;
}

message HelloReply {
  string message = 1;
}
```
服务方法和消息在 .proto 中定义，生成的客户端桩和服务端代码用于发起和处理 RPC。

### 工业级 RPC 框架
手写的 mock RPC 虽然实现了基本功能，但很简陋：没有错误重试、没有负载均衡、没有服务发现、没有流式传输、没有安全认证……而且每次都要自己处理 TCP 连接、JSON 编解码、路由分发。
gRPC 和 Kitex 就是工业级的 RPC 框架，它们把上面这些繁琐但通用的功能都给做好了，只需要关心业务逻辑。它们都遵循“定义 .proto → 生成代码 → 实现服务 → 启动服务”的模式。
- gRPC 是 Google 开源的，主打多语言、高性能，默认使用 Protobuf，支持 HTTP/2。
- Kitex 是字节跳动的，主要面向 Go 语言，支持多种协议（Thrift、Protobuf 等），在内部大规模使用。

## gRPC Hello World

