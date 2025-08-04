# TypeScript 自学笔记

## 学习目标

掌握 TypeScript 的核心概念和开发技能，能够使用 TypeScript 进行前端和后端开发。

## 核心概念

### 类型系统
- **静态类型检查**: 编译时类型检查
- **类型推断**: 自动推断变量类型
- **类型注解**: 显式声明类型

### 面向对象
- **类**: 类的定义和继承
- **接口**: 接口定义和实现
- **泛型**: 类型参数化

### 模块系统
- **ES6 模块**: import/export 语法
- **命名空间**: namespace 关键字
- **模块解析**: 模块查找策略

## 学习路径

### 第一阶段：基础语法
1. **基本类型**
```typescript
// 基本类型
let name: string = '包博文'
let age: number = 25
let isStudent: boolean = true
let hobbies: string[] = ['编程', '阅读', '运动']
let tuple: [string, number] = ['包博文', 25]

// 枚举
enum Color {
  Red = 'red',
  Green = 'green',
  Blue = 'blue'
}

// 联合类型
let id: string | number = '123'
id = 123

// 类型别名
type UserId = string | number
type User = {
  id: UserId
  name: string
  age: number
}
```

2. **函数类型**
```typescript
// 函数类型注解
function add(a: number, b: number): number {
  return a + b
}

// 箭头函数
const multiply = (a: number, b: number): number => a * b

// 可选参数和默认参数
function greet(name: string, greeting?: string): string {
  return greeting ? `${greeting}, ${name}!` : `Hello, ${name}!`
}

// 函数重载
function process(x: number): number
function process(x: string): string
function process(x: number | string): number | string {
  if (typeof x === 'number') {
    return x * 2
  }
  return x.toUpperCase()
}
```

3. **接口**
```typescript
// 接口定义
interface User {
  id: number
  name: string
  email: string
  age?: number
  readonly createdAt: Date
}

// 接口实现
class UserImpl implements User {
  constructor(
    public id: number,
    public name: string,
    public email: string,
    public readonly createdAt: Date
  ) {}
}

// 接口扩展
interface Employee extends User {
  department: string
  salary: number
}

// 函数接口
interface SearchFunc {
  (source: string, subString: string): boolean
}
```

### 第二阶段：高级特性
1. **泛型**
```typescript
// 泛型函数
function identity<T>(arg: T): T {
  return arg
}

// 泛型接口
interface GenericIdentityFn<T> {
  (arg: T): T
}

// 泛型类
class GenericNumber<T> {
  zeroValue: T
  add: (x: T, y: T) => T
}

// 泛型约束
interface Lengthwise {
  length: number
}

function loggingIdentity<T extends Lengthwise>(arg: T): T {
  console.log(arg.length)
  return arg
}
```

2. **高级类型**
```typescript
// 交叉类型
type Combined = User & Employee

// 联合类型
type Status = 'loading' | 'success' | 'error'

// 映射类型
type Partial<T> = {
  [P in keyof T]?: T[P]
}

type Required<T> = {
  [P in keyof T]-?: T[P]
}

// 条件类型
type NonNullable<T> = T extends null | undefined ? never : T

// 模板字面量类型
type EmailLocaleIDs = "welcome_email" | "email_heading"
type FooterLocaleIDs = "footer_title" | "footer_sendoff"
type AllLocaleIDs = `${EmailLocaleIDs | FooterLocaleIDs}_id`
```

3. **装饰器**
```typescript
// 类装饰器
function sealed(constructor: Function) {
  Object.seal(constructor)
  Object.seal(constructor.prototype)
}

@sealed
class Greeter {
  greeting: string
  constructor(message: string) {
    this.greeting = message
  }
  greet() {
    return "Hello, " + this.greeting
  }
}

// 方法装饰器
function log(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
  const method = descriptor.value
  
  descriptor.value = function (...args: any[]) {
    console.log(`Calling ${propertyKey} with:`, args)
    const result = method.apply(this, args)
    console.log(`Result:`, result)
    return result
  }
}

class Calculator {
  @log
  add(a: number, b: number): number {
    return a + b
  }
}
```

### 第三阶段：实战应用
1. **React + TypeScript**
```typescript
// 组件 Props 类型
interface UserCardProps {
  user: User
  onEdit?: (user: User) => void
  onDelete?: (id: number) => void
}

const UserCard: React.FC<UserCardProps> = ({ user, onEdit, onDelete }) => {
  return (
    <div className="user-card">
      <h3>{user.name}</h3>
      <p>{user.email}</p>
      {onEdit && <button onClick={() => onEdit(user)}>编辑</button>}
      {onDelete && <button onClick={() => onDelete(user.id)}>删除</button>}
    </div>
  )
}

// Hook 类型
function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      return initialValue
    }
  })

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.error(error)
    }
  }

  return [storedValue, setValue] as const
}
```

2. **Node.js + TypeScript**
```typescript
// Express 应用
import express, { Request, Response, NextFunction } from 'express'

interface UserRequest extends Request {
  user?: User
}

const app = express()

// 中间件类型
const authMiddleware = (req: UserRequest, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split(' ')[1]
  if (!token) {
    return res.status(401).json({ message: '未授权' })
  }
  // 验证 token 并设置用户信息
  req.user = { id: 1, name: '包博文', email: 'test@example.com' }
  next()
}

// 路由处理
app.get('/api/users/:id', authMiddleware, (req: UserRequest, res: Response) => {
  const userId = parseInt(req.params.id)
  const user = req.user
  
  res.json({ user, requestedId: userId })
})
```

## 最佳实践

### 类型安全
- **严格模式**: 启用严格类型检查
- **类型推断**: 充分利用类型推断
- **类型断言**: 谨慎使用类型断言

### 代码组织
- **模块化**: 合理组织代码模块
- **命名规范**: 统一的命名规范
- **文档注释**: 完善的类型注释

### 性能优化
- **编译优化**: 配置编译选项
- **类型检查**: 优化类型检查性能
- **打包优化**: 生产环境优化

## 学习资源

### 官方文档
- [TypeScript 官方文档](https://www.typescriptlang.org/)
- [TypeScript 中文手册](https://typescript.bootcss.com/)

### 在线课程
- TypeScript 官方教程
- 慕课网 TypeScript 课程
- 极客时间 TypeScript 专栏

### 实践项目
- 开源项目贡献
- 个人项目重构
- 企业项目开发

## 学习心得

### 学习建议
1. **循序渐进**: 从基础语法开始学习
2. **实践为主**: 多写代码，多调试
3. **类型思维**: 培养类型化思维
4. **工具使用**: 熟练使用开发工具

### 常见问题
1. **类型错误**: 理解类型错误信息
2. **配置问题**: 正确配置 TypeScript
3. **集成问题**: 与其他工具集成
4. **性能问题**: 优化编译和运行性能 