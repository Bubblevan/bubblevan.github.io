---
date: 2026-03-15
title: ThriftGo 与 IDL
authors: [bubblevan]
tags: []
---

IDL 的全称是 Interface Description Language（接口描述语言）。在微服务架构中，它的核心作用是 定义服务之间通信的契约。
在 Thrift 的语境下，IDL 文件（通常以 .thrift 结尾）定义了：
- 数据结构（struct）：请求和响应长什么样
- 服务接口（service）：有哪些方法可以调用
- 常量、枚举、类型别名等
一旦定义了 IDL，就可以用工具（如 thriftgo）为不同语言（Go、Java、Python 等）生成对应的代码。这样，服务提供方和服务消费方虽然用不同语言编写，但通信的数据格式和方法签名是完全一致的。

## ThriftGo
thriftgo 是 CloudWeGo（字节跳动开源）用 Go 语言实现的 Thrift 编译器，是 Apache Thrift 编译器的高效替代品。
给定一个简单的 IDL 文件 `hello.thrift`：
```thrift
// hello.thrift
namespace go hello.example

struct HelloReq {
    1: string Name
}

struct HelloResp {
    1: string RespBody
}

service HelloService {
    HelloResp HelloMethod(1: HelloReq request)
}
```
### 命名空间
其指定了生成代码时所属的包名/模块名，从而避免不同语言间的命名冲突：
```
namespace 语言名称 包路径
```
所以我们用`namespace go hello.example`时import的包名就是`hello.example`
#### 结构体（Struct）
其字段格式要求为：
```
字段ID: 字段类型 字段名称
```
- `1:`是字段的唯一数字标识，必须唯一，在**序列化**时用来标识字段（而非字段名）。
- 除`string`外，Thrift还支持`bool`、`i32`、`double`，容器如`list`、`map`以及其他自定义类型如其他`struct`
- `Name`的字段名称会成为生成的代码中结构体的字段名，通常首字母大写
- **可选修饰符**：`1: required string Name`
  - `required`：表示字段必须在请求中提供，否则会报错。
  - `optional`：表示字段可以省略，默认值为该类型的零值（如空字符串、0 等）。
| 类型 | 说明 | 示例 |
|------|------|------|
| **基础类型** | | |
| `bool` | 布尔值 | `true` / `false` |
| `byte` | 有符号字节 | `-128` 到 `127` |
| `i8` / `i16` / `i32` / `i64` | 有符号整数 | `i32 id` |
| `double` | 双精度浮点数 | `double price` |
| `string` | 字符串 | `string name` |
| `binary` | 二进制数据（字节数组） | `binary image` |
| **容器类型** | | |
| `list<T>` | 有序列表，元素类型 T | `list<string> tags` |
| `set<T>` | 无序集合，元素唯一 | `set<i64> ids` |
| `map<K, V>` | 键值对 | `map<string, i32> counts` |
| **自定义类型** | 之前定义的结构体、枚举等 | `HelloReq req` |

> **序列化**
> 一个典型的Thrift二进制编码（以紧凑协议 TCompactProtocol 为例）大致是：`[字段ID和类型标志] [值的长度（如果是变长类型）] [值本身]`
> 比如`1: string Name = "Alice"`，序列化后可能类似：`0x0B 0x01 0x05 0x41 0x6C 0x69 0x63 0x65`
> - 0x0B：类型标志，表示这是一个string（Thrift类型ID为11）。
> - 0x01：字段ID（1）与类型打包后的结果（简化）。
> - 0x05：字符串长度5。
> - 0x41...：字符串 "Alice" 的ASCII码。
> 这样，反序列化时，解析器先读类型和ID，知道是字段1的string，然后读长度，接着读对应字节得到值。

#### 服务（Service）
定义一个RPC服务接口，类似Go里的interface，格式为：
```
返回类型 方法名(参数列表)
```
- 参数列表里，每个参数同样必须包含`参数ID: 参数类型 参数名称`
- `(1: i32 a, 2: i32 b)`即为多个参数
- 还可以跑出异常（下面就是**自定义异常**）
```thrift
exception InvalidOperation {
  1: i32 code,
  2: string message
}

service Calculator {
  i32 add(1:i32 a, 2:i32 b) throws (1:InvalidOperation e)
}
```
#### 枚举
```thrift
enum Status {
  OK = 200,
  NOT_FOUND = 404,
  INTERNAL_ERROR = 500
}
```
#### 常量
```thrift
const i32 MAX_RETRIES = 3
const string SERVICE_NAME = "payment"
```
#### 类型别名
```thrift
typedef i64 UserID
```
主要作用是为已有类型起一个新名字增强可读性的。
#### 引入其他IDL
```thrift
include "base.thrift"
```
可以引入其他 `.thrift` 文件，实现模块化。被引入的文件中定义的 struct、service 等可以在当前文件中使用。
### 生成代码示例（Go）
`thriftgo -g go hello.thrift`得到的Go代码形似：
```go
// 包名取自 namespace 最后一段，这里可能是 example
package example

// HelloReq 结构体
type HelloReq struct {
    Name string `thrift:"name,1" json:"name"`
}

func NewHelloReq() *HelloReq {
    return &HelloReq{}
}

// HelloResp 结构体
type HelloResp struct {
    RespBody string `thrift:"respBody,1" json:"respBody"`
}

func NewHelloResp() *HelloResp {
    return &HelloResp{}
}

// HelloService 接口
type HelloService interface {
    HelloMethod(ctx context.Context, req *HelloReq) (*HelloResp, error)
}
```
此外还会生成客户端和服务端的代码框架。