# Nest.js 自学笔记

## 框架概述

Nest (NestJS) 是一个专为构建高效、可扩展的 Node.js 服务器端应用而设计的框架。它采用了渐进式 JavaScript 的设计理念，完全支持 TypeScript 开发，同时保持了使用纯 JavaScript 编码的灵活性。Nest.js 巧妙地将面向对象编程(OOP)、函数式编程(FP)和函数式反应式编程(FRP)的元素融合在一起，为开发者提供了一个结构清晰、易于维护的开发框架。

在底层架构上，Nest.js 构建在强大的 HTTP 服务器框架之上。默认情况下使用 Express 作为底层引擎，但通过配置也可以无缝切换到 Fastify。这意味着开发者可以根据项目需求选择使用 Express 的 API 或者 Fastify 的 API，享受不同框架的优势。

## 为什么选择 Nest.js

选择 Nest.js 作为后端开发框架有多个重要原因。首先，它提供了严格的模块分类机制，让代码组织更加清晰有序。其次，Nest.js 的学习曲线相对平缓，上手容易，同时拥有丰富的学习资源和活跃的社区支持。最重要的是，它能够充分利用 TypeScript 的严格类型系统来规范代码质量，这对于构建大型应用来说至关重要。

从开发效率角度来看，Nest.js 的热更新机制采用了增量更新策略，这意味着在开发过程中只有发生变化的文件会被重新编译，大大提升了开发时的响应速度。从个人开发体验来说，Nest.js 使用装饰器语法编写代码，这种风格与 Java 的注解系统非常相似，对于有 Java 背景的开发者来说会感到非常熟悉，能够快速适应并提高开发效率。

## 项目创建与环境搭建

### 环境准备

在开始使用 Nest.js 之前，首先需要确保你的操作系统上安装了 Node.js，版本要求不低于 16。Node.js 的安装相对简单，可以从官网下载安装包进行安装。

### 项目初始化

使用 Nest.js 的命令行接口来创建新项目非常简单，只需要在终端中输入以下命令：

```bash
npm i -g @nestjs/cli
nest new project-name
```

第一条命令会全局安装 Nest.js 的 CLI 工具，第二条命令会创建一个新的项目目录并自动安装所有必要的依赖。CLI 工具会自动生成项目的基础结构和配置文件，让你能够立即开始开发。

### 项目结构解析

创建完成后，在 `src` 目录下会生成一些 Nest.js 标准的文件，这些文件构成了应用的基础架构：

- **app.controller.spec.ts**: 这是 `app.controller` 的单元测试文件，用于编写控制器相关的测试用例
- **app.controller.ts**: 控制器文件，主要负责处理 HTTP 请求和调用 service 层的处理方法，路由管理通常在这里进行
- **app.module.ts**: 根模块文件，用于处理其他类的引用与共享，通常以 module 文件夹来组织不同的功能模块
- **app.service.ts**: 服务文件，封装通用的业务逻辑、与数据层的交互（例如数据库操作）、以及其他第三方服务的请求
- **main.ts**: 应用程序的入口文件，使用 NestFactory 来创建 Nest 应用实例

## 应用启动与运行

### 启动命令

安装完成后，可以通过查看 `package.json` 文件来了解可用的启动命令。最基本的启动命令是：

```bash
npm run start
```

这个命令会启动应用，但不会监听文件变化。如果你希望在开发过程中实现自动重新编译和重新加载服务器，可以使用：

```bash
npm run start:dev
```

这个命令会启动文件监视模式，当代码发生变化时会自动重新编译并重启服务，大大提升了开发效率。

### 入口文件分析

启动服务后，首先需要了解入口文件 `main.ts` 的工作原理：

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
    const app = await NestFactory.create(AppModule);
    await app.listen(process.env.PORT ?? 3000);
}
bootstrap();
```

从这段代码可以看出，应用启动过程分为两个主要步骤：首先使用 Nest.js 的工厂函数 `NestFactory` 来创建一个 `AppModule` 实例，然后通过 `app.listen` 来监听指定的端口。端口号可以通过环境变量 `PORT` 来自定义，如果没有设置则默认使用 3000 端口。

需要注意的是，如果 3000 端口被占用，可以在 `main.ts` 里面修改默认端口号，或者创建 `.env` 文件来自定义端口号。启动成功后，在浏览器中访问 `http://localhost:3000` 就能看到应用的运行状态。

## 模块系统详解

### 根模块结构

从 `main.ts` 中可以看出，应用只导入了 `AppModule`，让我们深入查看 `app.module.ts` 文件：

```typescript
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { UserController } from './user/user.controller';

@Module({
    imports: [],
    controllers: [AppController, UserController],
    providers: [AppService],
})
export class AppModule {}
```

`AppModule` 是应用程序的根模块，它提供了启动应用的引导机制，可以包含多个功能模块。每个 `.module` 文件都需要使用 `@Module()` 装饰器，这个装饰器接收四个重要属性：

- **providers**: 提供者数组，包含服务、工厂等可注入的类
- **controllers**: 控制器数组，定义该模块中可用的控制器
- **imports**: 导入模块列表，用于引入其他模块导出的提供者
- **exports**: 导出数组，指定该模块提供的、可以被其他模块使用的提供者

### 模块创建与组织

为了保持代码的清晰界限，Nest.js 提供了强大的模块化能力。你可以使用 CLI 命令快速生成不同类型的模块：

- 使用 `nest g mo` 生成模块来组织代码
- 使用 `nest g co` 生成控制器来定义 CRUD 路径
- 使用 `nest g s` 生成服务来表示和隔离业务逻辑
- 使用 `nest g resource` 生成完整的 CRUD 功能模块

值得注意的是，使用命令创建 `UserController` 的同时，CLI 会自动在 `app.module.ts` 里面注册对应的 Controller，减少了手动配置的工作量。

### 共享模块与全局模块

在 Nest.js 中，默认情况下模块是单例的，这意味着你可以轻松地在多个模块之间共享任何提供者的同一实例。每个模块自动成为共享模块，一旦创建就可以被任何模块重用。

如果你想要在其他几个模块之间共享 `UserService` 的实例，需要将 `UserService` 提供者添加到模块的 `exports` 数组中：

```typescript
import { Module } from '@nestjs/common';
import { UserService } from './user.service';
import { UserController } from './user.controller';

@Module({
    controllers: [UserController],
    providers: [UserService],
    exports: [UserService]
})
export class UserModule {}
```

对于需要在所有地方导入的相同模块集，可以使用 `@Global()` 装饰器使模块全局化。全局模块应该只注册一次，通常由根模块或核心模块注册。

## 控制器与路由系统

### 控制器基础

控制器负责处理传入的请求并向客户端返回响应。控制器的目的是接收应用的特定请求，路由机制控制哪个控制器接收哪些请求。通常，每个控制器都有多条路由，不同的路由可以执行不同的操作。

`@Controller()` 装饰器是定义基本控制器所必需的，该装饰器可以传入一个路径参数，作为访问这个控制器的主路径。如果不传参数，则表示使用默认路径。

### 请求处理与装饰器

处理程序通常需要访问客户端请求的详细信息。通过将 `@Req()` 装饰器添加到处理程序的签名中，可以指示 Nest.js 注入请求对象来访问请求信息：

```typescript
import { Controller, Get, Req } from '@nestjs/common';
import { Request } from 'express';

@Controller('user')
export class UserController {
    @Get()
    getHello(@Req() request: Request): string {
        console.log(request);
        return 'Hello Nest.js!';
    }
}
```

请求对象表示 HTTP 请求，具有请求查询字符串、参数、HTTP 标头和正文等属性。在大多数情况下，没有必要手动获取这些属性，Nest.js 提供了开箱即用的专用装饰器，如 `@Body()` 或 `@Query()`。

### HTTP 方法装饰器

Nest.js 为所有标准的 HTTP 方法提供装饰器：`@Get()`、`@Post()`、`@Put()`、`@Delete()`、`@Patch()`、`@Options()` 和 `@Head()`。此外，`@All()` 定义了一个端点来处理所有这些方法：

```typescript
import { Controller, Delete, Get, Patch, Post, Put } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
    constructor(private readonly appService: AppService) {}

    @Get()
    getHello(): string {
        return this.appService.getHello();
    }

    @Get('/list')
    getHelloList(): string {
        return '这是list页面';
    }

    @Post('/list')
    create(): string {
        return 'post请求页面';
    }

    @Put('/list')
    update(): string {
        return 'put请求页面';
    }

    @Delete('/list')
    delete(): string {
        return 'delete请求页面';
    }

    @Patch('/list')
    patch(): string {
        return 'patch请求页面';
    }
}
```

### 路由参数与请求负载

当需要接受动态数据作为请求的一部分时（例如，GET /cats/1 获取 ID 为 1 的 cat），可以使用路由参数。在路由的路径中添加路由参数标记，使用 `@Param()` 装饰器访问这些参数：

```typescript
@Get(':id')
findOne(@Param() params: any): string {
    console.log(params.id);
    return `This action returns a #${params.id} cat`;
}
```

对于 POST 路由处理程序，如果客户端需要传递参数，可以使用 `@Body()` 装饰器。但首先需要确定 DTO（数据传输对象）架构。DTO 是定义数据如何通过网络发送的对象，可以通过 TypeScript 接口或类来确定：

```typescript
export class CreateCatDto {
    name: string;
    age: number;
    breed: string;
}

@Post()
async create(@Body() createCatDto: CreateCatDto) {
    return 'This action adds a new cat';
}
```

## 中间件与异常处理

### 中间件机制

中间件是在路由处理程序之前调用的函数，中间件函数可以访问 request 和 response 对象，以及应用请求-响应周期中的 `next()` 中间件函数。中间件函数能够执行各种任务，如验证请求、解析请求体、处理错误等。

你可以在函数中或在具有 `@Injectable()` 装饰器的类中实现自定义 Nest 中间件：

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    console.log('Request...');
    next();
  }
}
```

### 中间件应用

使用模块类的 `configure()` 方法设置中间件，包含中间件的模块必须实现 `NestModule` 接口：

```typescript
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware';
import { CatsModule } from './cats/cats.module';

@Module({
    imports: [CatsModule],
})
export class AppModule implements NestModule {
    configure(consumer: MiddlewareConsumer) {
        consumer
        .apply(LoggerMiddleware)
        .forRoutes('cats');
    }
}
```

### 异常过滤器

异常过滤器负责处理应用中所有未处理的异常。当应用代码未处理异常时，该层会捕获异常，然后自动发送适当的用户友好响应。

Nest.js 提供了一个内置的 `HttpException` 类，可以抛出标准异常：

```typescript
@Get()
async findAll() {
    throw new HttpException('Forbidden', HttpStatus.FORBIDDEN);
}
```

如果内置的异常不能满足需求，可以创建自定义异常。通过扩展基类 `HttpException`，自定义异常将与内置异常处理程序无缝协作：

```typescript
export class ForbiddenException extends HttpException {
    constructor() {
        super('Forbidden', HttpStatus.FORBIDDEN);
    }
}
```

## 管道与验证

### 管道基础

管道是用 `@Injectable()` 装饰器注释的类，它实现了 `PipeTransform` 接口。管道有两个典型的用例：转型和验证。转型将输入数据转换为所需的形式，验证评估输入数据，如果有效则传递，否则抛出异常。

### 管道绑定

要使用管道，需要将管道类的实例绑定到适当的上下文。如果希望将管道与特定的路由处理程序方法相关联，可以在方法参数级别绑定管道：

```typescript
@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number) {
    return this.catsService.findOne(id);
}
```

### 自定义管道

每个管道都必须实现 `transform()` 方法来履行 `PipeTransform` 接口契约。这个方法有两个参数：`value` 参数是当前处理的方法参数，`metadata` 是当前处理的方法参数的元数据。

### 全局管道

使用 `useGlobalPipes` 实现全局作用域管道，使其应用于整个应用中的每个路由处理程序：

```typescript
async function bootstrap() {
    const app = await NestFactory.create(AppModule);
    app.useGlobalPipes(new ValidationPipe());
    await app.listen(3000);
}
bootstrap();
```

## 守卫与拦截器

### 守卫机制

守卫是一个用 `@Injectable()` 装饰器注释的类，它实现了 `CanActivate` 接口。守卫有单一的责任，它们根据运行时存在的某些条件（如权限、角色、ACL 等）确定给定请求是否将由路由处理程序处理，这通常称为授权。

守卫在所有中间件之后、任何拦截器或管道之前执行，是处理身份验证和授权的理想选择。

### 拦截器系统

拦截器是用 `@Injectable()` 装饰器注释并实现 `NestInterceptor` 接口的类。每个拦截器都实现了 `intercept()` 方法，它有两个参数：第一个是 `ExecutionContext` 实例，第二个参数是 `CallHandler`。

`CallHandler` 接口实现了 `handle()` 方法，你可以使用它在拦截器中的某个点调用路由处理程序方法。如果在 `intercept()` 方法的实现中不调用 `handle()` 方法，则根本不会执行路由处理程序方法。

## 数据库集成与 TypeORM

### 为什么选择 MySQL 和 TypeORM

作为后端项目，数据库连接是必不可少的。MySQL 作为关系型数据库，应用广泛且非常稳定，拥有非常活跃的社区支持。TypeORM 作为 Node.js 中老牌的 ORM 框架，无论是接口定义还是代码实现方面都简单易懂、可读性高，也很容易对接多种数据源。

TypeORM 使用 TypeScript 编写，在 NestJS 框架下运行得非常好，也是 NestJS 首推的 ORM 框架，有开箱即用的 `@nestjs/typeorm` 软件包支持。

### 环境配置

NestJS 自带了多环境配置方法，使用 `@nestjs/config` 会默认从项目根目录载入并解析一个 `.env` 文件。首先需要安装依赖：

```bash
npm i @nestjs/config -S
```

安装完毕后，在 `app.module.ts` 中添加 `ConfigModule` 模块：

```typescript
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { UserModule } from './user/user.module';
import { ConfigModule } from '@nestjs/config';

@Module({
    imports: [ConfigModule.forRoot(), UserModule],
    controllers: [AppController],
    providers: [AppService],
})
export class AppModule {}
```

### 数据库连接方式

NestJS 使用 TypeORM 的方式有两种。一种是使用 NestJS 提供的 `@nestjs/typeorm` 集成包，另一种是直接使用 `typeorm` 自由封装 Providers。

#### 使用 @nestjs/typeorm 连接数据库

首先安装依赖：

```bash
npm i @nestjs/typeorm typeorm mysql2 -S
```

在根目录下创建 `.env` 文件存放数据库配置信息：

```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWD=root
DB_DATABASE=blog
```

在 `app.module.ts` 中连接数据库：

```typescript
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigService, ConfigModule } from '@nestjs/config';
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { UserModule } from './user/user.module';
import * as path from 'path';

const envPath = path.resolve('.env');

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: [envPath],
    }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: async (configService: ConfigService) => ({
        type: 'mysql',
        entities: [],
        host: configService.get('DB_HOST', 'localhost'),
        port: configService.get<number>('DB_PORT', 3306),
        username: configService.get('DB_USER', 'root'),
        password: configService.get('DB_PASSWORD', 'root'),
        database: configService.get('DB_DATABASE', 'blog'),
        timezone: '+08:00',
        synchronize: true,
      }),
    }),
    UserModule
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
```

## CRUD 操作实现

### 实体定义

通过 TypeORM 连接好数据库后，需要创建数据表实体，并通过接口实现 CRUD 功能。创建 `user.entity.ts` 实例：

```typescript
import { Column, Entity, PrimaryGeneratedColumn } from "typeorm";

@Entity('user')
export class User {
    @PrimaryGeneratedColumn()
    id: number;
    
    @Column({ default: null })
    name: string;
    
    @Column({type: 'timestamp', default: () => "CURRENT_TIMESTAMP"})
    create_time: Date;
    
    @Column({type: 'timestamp', default: () => "CURRENT_TIMESTAMP"})
    update_time: Date;
}
```

### 服务层实现

修改 `user.service.ts` 文件，实现 CRUD 操作：

```typescript
import { HttpException, Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './entities/user.entity';

@Injectable()
export class UserService {
    constructor(
        @InjectRepository(User)
        private readonly userRepository: Repository<User>,
    ) {}

    async create(createUserDto: Partial<User>): Promise<User> {
        const { name } = createUserDto;
        if (!name) {
            throw new HttpException('名字不能为空', 401);
        }
        const userInfo = await this.userRepository.findOne({ where: { name } });
        if (userInfo) {
            throw new HttpException('名称不能重复', 401);
        }
        return await this.userRepository.create(createUserDto);
    }

    async findById(id): Promise<User> {
        return await this.userRepository.findOne(id);
    }

    async updateById(id, user): Promise<User> {
        const existUser = await this.userRepository.findOne(id);
        if (!existUser) {
            throw new HttpException('用户不存在', 401);
        }
        const updateUser = this.userRepository.merge(existUser, user);
        return this.userRepository.save(updateUser);
    }

    async remove(id) {
        const existUser = await this.userRepository.findOne(id);
        if (!existUser) {
            throw new HttpException('用户不存在', 401);
        }
        return await this.userRepository.remove(existUser);
    }
}
```

### 控制器层实现

在 `user.controller.ts` 中添加相关路由：

```typescript
import {
    Controller,
    Get,
    Post,
    Body,
    Patch,
    Param,
    Delete,
    Put,
} from '@nestjs/common';
import { UserService } from './user.service';

@Controller('user')
export class UserController {
    constructor(private readonly userService: UserService) {}

    @Post()
    async create(@Body() createUserDto) {
        return await this.userService.create(createUserDto);
    }

    @Get(':id')
    async findById(@Param('id') id: string) {
        return await this.userService.findById(id);
    }

    @Put(':id')
    async update(@Param('id') id: string, @Body() updateUserDto) {
        return await this.userService.updateById(id, updateUserDto);
    }

    @Delete(':id')
    async remove(@Param('id') id: string) {
        return await this.userService.remove(id);
    }
}
```

### 模块配置

在 `user.module.ts` 中加上相关引入：

```typescript
import { Module } from '@nestjs/common';
import { UserService } from './user.service';
import { UserController } from './user.controller';
import { TypeOrmModule } from '@nestjs/typeorm';
import { User } from './entities/user.entity';

@Module({
    imports: [TypeOrmModule.forFeature([User])],
    controllers: [UserController],
    providers: [UserService],
})
export class UserModule {}
```

## 接口文档与 Swagger

### 为什么选择 Swagger

作为后端接口，接口文档是必不可少的。选择 Swagger 的原因一方面是 Nest.js 提供了专用的模块来使用它，其次它可以精确地展示每个字段的意义，只要注解写得到位，就能生成清晰完整的 API 文档。

### 安装与配置

首先安装依赖：

```bash
npm i @nestjs/swagger -S
```

创建 `doc.ts` 文件来配置 Swagger：

```typescript
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import * as packageConfig from '../package.json'

export const generateDocument = (app) => {
  const options = new DocumentBuilder()
    .setTitle(packageConfig.name)
    .setDescription(packageConfig.description)
    .setVersion(packageConfig.version)
    .build();

  const document = SwaggerModule.createDocument(app, options);
  SwaggerModule.setup('/api/doc', app, document);
}
```

为了方便，Swagger 的配置信息都从 `package.json` 中获取。默认情况下，TypeScript 项目中不能直接导入 `.json` 模块，所以需要在 `tsconfig.json` 中新增 `resolveJsonModule: true` 配置。

### 在 main.ts 中引入

在 `main.ts` 中引入方法即可：

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { generateDocument } from './doc';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  generateDocument(app);
 
  await app.listen(process.env.PORT ?? 3000);
}
bootstrap();
```

### 接口标签配置

在对应的 controller 文件中加入 `@ApiTags` 装饰器：

```typescript
import {
    Controller,
    Get,
    Post,
    Body,
    Patch,
    Param,
    Delete,
    Put,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { UserService } from './user.service';

@ApiTags('用户')
@Controller('user')
export class UserController {
    // ... 其他代码
}
```

通过上述操作后，启动服务，在浏览器输入 `http://localhost:3000/api/doc` 就可以看到生成的 API 文档了。

## 总结与展望

通过本文的学习，我们已经掌握了 Nest.js 框架的核心概念和基本使用方法。从项目创建、模块系统、控制器路由、数据库集成到接口文档生成，形成了一个完整的开发流程。

这只是 Nest.js 学习之旅的开始，后面还会有更多复杂的场景等待探索，比如微服务架构、GraphQL 集成、测试策略、部署监控等。Nest.js 作为一个成熟的企业级框架，提供了丰富的功能和良好的扩展性，值得深入学习和实践。

继续努力，加油！