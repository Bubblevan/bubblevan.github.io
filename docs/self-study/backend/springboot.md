Spring Boot 自学笔记：从零到实践，构建高效Java后端应用
Spring Boot 介绍
Spring Boot 是一个用于构建高效、可独立运行的、生产级别的 Spring 应用程序的框架。它基于 Spring 框架，但极大地简化了初始搭建和开发过程。Spring Boot 遵循“约定优于配置”的原则，通过大量的自动配置，让开发者可以快速启动并运行一个项目，而无需深陷于繁杂的 XML 配置中。

在底层，Spring Boot 内嵌了诸如 Tomcat、Jetty 或 Undertow 这样的 Web 服务器，这意味着你不需要将应用打包成 WAR 文件部署到外部服务器，而是可以直接运行一个 JAR 文件。它完美地整合了 Spring 生态系统中的各种项目（如 Spring MVC, Spring Data），并为第三方库提供了大量的“starter”依赖，极大地简化了依赖管理。

详情可以查阅 Spring Boot 官方文档。

为什么选择 Spring Boot
选择一个框架，往往是基于其生态、效率和稳定性。Spring Boot 在这些方面都表现出色：

庞大的生态与社区：作为 Java 世界事实上的标准，Spring 拥有无与伦比的社区支持和丰富的学习资源。遇到任何问题，你几乎都能找到解决方案。

开发效率：Spring Initializr 让我们可以在几秒钟内创建一个功能完备的项目骨架。“约定优于配置”和自动配置让我们能专注于业务逻辑，而不是框架的配置。

稳定与成熟：在无数企业级应用中得到了验证，Spring Boot 的稳定性和性能毋庸置疑。对于构建大型、复杂的系统来说，这是一个非常可靠的选择。

说了这么多，接下来让我们正式踏上 Spring Boot 的学习之旅吧！本文将主要涵盖以下内容：

创建一个 Spring Boot 项目
首先，确保你的系统上安装了 Java Development Kit (JDK)（推荐版本 >= 11）和构建工具 Maven 或 Gradle。创建 Spring Boot 项目最便捷的方式是使用 Spring Initializr。

你可以直接访问 start.spring.io，或者通过你的 IDE（如 IntelliJ IDEA Ultimate）内置的 Spring Initializr 功能来创建。

我们选择以下配置：

Project: Maven Project

Language: Java

Spring Boot: 选择一个稳定的版本 (如 3.x.x)

Project Metadata: 填写你自己的 Group 和 Artifact

Dependencies: 添加 Spring Web（用于构建 Web 应用）、Spring Data JPA（用于数据库操作）、MySQL Driver（连接 MySQL 数据库）和 Lombok（简化代码的工具）。

点击 "Generate"，下载并解压项目，然后用你的 IDE 打开。

项目文件介绍
除去 Maven 的标准目录结构和配置文件之外，在 src/main/java 目录下，我们会看到一些 Spring Boot 的核心文件：

src
└── main
    ├── java
    │   └── com
    │       └── example
    │           └── demo
    │               └── DemoApplication.java  // 主程序入口
    └── resources
        ├── application.properties          // 核心配置文件
        ├── static
        └── templates
pom.xml                                     // Maven 依赖与构建配置
文件名	文件描述
DemoApplication.java	应用程序的入口文件。它包含一个 main 方法，使用 SpringApplication.run() 来启动整个应用。
application.properties	Spring Boot 的核心配置文件，用于配置应用端口、数据库连接、日志级别等各种属性。
pom.xml	Maven 项目的配置文件，定义了项目信息、依赖库（starters）和构建插件。

导出到 Google 表格
项目运行
Maven 依赖下载完成后，你可以直接在 IDE 中找到 DemoApplication.java 文件，右键点击并选择 "Run"。或者在项目根目录下打开终端，输入以下命令：

Bash

mvn spring-boot:run
此命令会启动内嵌的 Tomcat 服务器并运行你的应用。服务启动后，我们来分析一下入口文件 DemoApplication.java：

Java

package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
代码非常简洁。核心是 @SpringBootApplication 这个注解，它是一个复合注解，包含了三个关键功能：

@EnableAutoConfiguration: 启用 Spring Boot 的自动配置机制，它会根据你添加的依赖（比如 spring-boot-starter-web）来猜测并配置你可能需要的 Bean。

@ComponentScan: 自动扫描该类所在包及其子包下的所有组件（如 @Component, @Service, @Controller 等）并注册到 Spring 容器中。

@Configuration: 允许在上下文中注册额外的 Bean 或导入其他配置类。

main 方法中的 SpringApplication.run() 则负责引导和启动整个 Spring 应用。

新增一个【用户模块】
遵循分层架构的思想，我们来手动创建一个简单的用户模块。一个典型的模块包含 Controller（控制器）、Service（服务）和 Repository（数据访问）层。

首先，我们通过命令行或在 IDE 中创建对应的包和类文件：

创建一个 user 包。

在 user 包下，创建一个 UserController.java。

然后，在 UserController 中编写一个简单的 HTTP 请求处理方法。

Java

package com.example.demo.user;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/user")
public class UserController {

    @GetMapping
    public String getHello() {
        return "Hello Spring Boot!";
    }
}
等待程序自动重新加载（如果你的 IDE 配置了），或者重启应用。在浏览器中访问 http://localhost:8080/user，你将看到页面上显示的 "Hello Spring Boot!"。

Spring Boot 控制器 (Controller)
控制器负责处理传入的 HTTP 请求，并将响应返回给客户端。它的核心任务是接收、解析请求，然后调用相应的服务来处理业务逻辑，最后封装并返回结果。路由机制决定了哪个控制器的哪个方法来处理特定请求。

@RestController & @RequestMapping
@RestController 是一个组合注解，它结合了 @Controller 和 @ResponseBody。@Controller 用于标识这是一个控制器类，而 @ResponseBody 则告诉 Spring，这个类中所有方法的返回值都应直接写入 HTTP 响应体中，而不是解析为视图（比如 JSP）。这对于构建 RESTful API 至关重要。

@RequestMapping("/user") 定义了这个控制器下所有请求的基础路径。

请求方法 (Resources)
Spring 为所有标准的 HTTP 方法提供了专门的注解，使得代码更具可读性：@GetMapping、@PostMapping、@PutMapping、@DeleteMapping、@PatchMapping。

Java

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    // 匹配 GET /api/users
    @GetMapping
    public String getAllUsers() {
        return "获取所有用户";
    }
    
    // 匹配 POST /api/users
    @PostMapping
    public String createUser() {
        return "创建新用户";
    }

    // 匹配 PUT /api/users
    @PutMapping
    public String updateUser() {
        return "更新用户";
    }

    // 匹配 DELETE /api/users
    @DeleteMapping
    public String deleteUser() {
        return "删除用户";
    }
}
路由参数 (Path Variables)
当需要从 URL 路径中捕获动态数据时（例如 GET /users/1 来获取 ID 为 1 的用户），可以使用路径变量。通过在路径中使用 {} 占位符，并使用 @PathVariable 注解来将这部分值绑定到方法参数上。

Java

@GetMapping("/{id}")
public String findOne(@PathVariable Long id) {
    System.out.println("Fetching user with id: " + id);
    return "This action returns user #" + id;
}
请求负载 (Request Body)
对于 POST 或 PUT 请求，客户端通常会在请求体中发送数据（例如 JSON）。我们可以使用 @RequestBody 注解来处理。

首先，我们需要定义一个 DTO (数据传输对象)，它是一个简单的 Java 类 (POJO)，用于映射传入的 JSON 数据。

Java

// 使用 Lombok 简化代码
import lombok.Data;

@Data
public class CreateUserDto {
    private String name;
    private int age;
    private String email;
}
然后，在控制器的方法中使用 @RequestBody 来接收这个 DTO。

Java

@PostMapping
public String create(@RequestBody CreateUserDto createUserDto) {
    return "Creating a new user with name: " + createUserDto.getName();
}
Spring Boot 会自动使用内置的 Jackson 库将请求体中的 JSON 字符串反序列化为 CreateUserDto 对象。

Spring 核心：依赖注入 (DI) 与 IoC 容器
Spring 的核心是控制反转 (Inversion of Control, IoC) 和 依赖注入 (Dependency Injection, DI)。简单来说，IoC 意味着你不再需要自己去创建和管理对象的生命周期 (new UserSerivce())，而是将这个控制权“反转”给了 Spring 容器。DI 则是实现 IoC 的一种方式：容器会主动将一个对象所依赖的其他对象“注入”给它。

模块化是通过组件 (Component) 和依赖注入来实现的。在 Spring 中，任何被 @Component 或其衍生注解（@Service, @Repository, @Controller）标记的类，都会被 Spring 容器扫描并管理。

假设我们需要一个 UserService 来处理业务逻辑。

Java

package com.example.demo.user;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    public String findUserById(Long id) {
        // 模拟从数据库查找用户
        return "Found user with id: " + id;
    }
}
@Service 注解表明这个类是一个业务逻辑组件。现在，我们可以在 UserController 中注入并使用它。推荐使用构造函数注入：

Java

@RestController
@RequestMapping("/user")
public class UserController {

    private final UserService userService;

    // 通过构造函数注入 UserService
    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/{id}")
    public String findOne(@PathVariable Long id) {
        return userService.findUserById(id);
    }
}
当 Spring 创建 UserController 实例时，它会发现构造函数需要一个 UserService 类型的参数，于是它会自动从容器中找到 UserService 的实例并传入。这就是依赖注入。

切面编程：拦截器、过滤器与异常处理
在 Web 开发中，我们经常需要处理一些横切关注点，如日志记录、权限验证、异常捕ăpadă等。Spring 提供了强大的机制来处理这些任务，其思想与 Nest.js 中的中间件、守卫、管道等类似。

过滤器 (Filter)
过滤器是 Java Servlet规范的一部分，它工作在请求处理的最外层，可以在请求到达 DispatcherServlet 之前或之后执行。它非常适合用于处理编码、日志记录、CORS 等底层任务。

Java

import jakarta.servlet.*;
import org.springframework.stereotype.Component;
import java.io.IOException;

@Component
public class LoggingFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) throws IOException, ServletException {
        System.out.println("Request received...");
        chain.doFilter(request, response); // 将请求传递给下一个过滤器或处理器
        System.out.println("Response sent...");
    }
}
拦截器 (Interceptor)
拦截器是 Spring MVC 提供的机制，它比过滤器更贴近业务，可以访问到将要处理请求的控制器方法 (Handler) 等上下文信息。它非常适合做权限验证、日志等。

要使用拦截器，需要实现 HandlerInterceptor 接口，并通过 WebMvcConfigurer 进行注册。

全局异常处理器 (Exception Filter)
这是处理应用中所有未捕获异常的最佳实践。通过创建一个带有 @ControllerAdvice 注解的类，我们可以定义处理特定异常的方法。

Java

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(Exception.class)
    public ResponseEntity<String> handleAllExceptions(Exception ex) {
        // 在这里可以记录日志
        return new ResponseEntity<>("An unexpected error occurred: " + ex.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<String> handleResourceNotFoundException(ResourceNotFoundException ex) {
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.NOT_FOUND);
    }
}
当任何控制器中抛出 ResourceNotFoundException 时，handleResourceNotFoundException 方法就会被调用，并返回一个 404 响应。

管道 (Pipes) -> 数据校验 (Validation)
在 Spring Boot 中，数据校验通常通过 spring-boot-starter-validation (它引入了 Hibernate Validator) 来实现。我们可以在 DTO 中使用 JSR 303/380 注解来声明校验规则。

Java

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class CreateUserDto {
    @NotEmpty(message = "Name cannot be empty")
    private String name;

    @Min(value = 18, message = "Age must be at least 18")
    private int age;

    @Email(message = "Invalid email format")
    private String email;
}
然后在控制器的方法参数上加上 @Valid 注解。

Java

@PostMapping
public String create(@Valid @RequestBody CreateUserDto createUserDto) {
    return "User created successfully!";
}
如果传入的 JSON 不符合规则，Spring 会自动抛出一个 MethodArgumentNotValidException，我们可以用前面提到的全局异常处理器来捕获它，并返回一个友好的错误信息。

MySQL 操作
后端应用离不开数据库。我们将使用 Spring Data JPA 来简化数据库操作。

什么是 Spring Data JPA?
JPA (Java Persistence API) 是 Java 的一个官方规范，用于对象关系映射 (ORM)。它定义了一套 API，但没有提供实现。Hibernate 是最流行的 JPA 实现。Spring Data JPA 则是 Spring 提供的一个模块，它在 JPA 的基础上再次进行了封装，提供了 Repository 编程模型，让你几乎不用写任何 SQL 语句就能完成大部分数据操作。

配置
首先，在 application.properties 文件中添加数据库连接信息：

Properties

# MySQL aettings
spring.datasource.url=jdbc:mysql://localhost:3306/blog?useSSL=false&serverTimezone=UTC
spring.datasource.username=root
spring.datasource.password=your_password
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver

# JPA settings
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
spring.jpa.hibernate.ddl-auto=update 会让 Hibernate 根据你的实体类自动更新数据库表结构，这在开发阶段非常方便。

实现 CRUD
创建实体 (Entity)
实体是一个映射到数据库表的 Java 类。我们使用 JPA 注解来定义映射关系。

Java

import jakarta.persistence.*;
import lombok.Data;
import java.util.Date;

@Entity
@Table(name = "user")
@Data
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    private String email;

    @Temporal(TemporalType.TIMESTAMP)
    private Date createTime;

    @PrePersist
    protected void onCreate() {
        createTime = new Date();
    }
}
创建仓库 (Repository)
创建一个接口，继承 JpaRepository。Spring Data JPA 会在运行时自动为这个接口提供实现。

Java

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, Long> {
    // 你还可以在这里定义自定义查询方法，比如
    // User findByName(String name);
}
修改 Service 和 Controller
现在，将 UserRepository 注入到 UserService 中，并实现完整的 CRUD 逻辑。

Java

@Service
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public User createUser(CreateUserDto dto) {
        User user = new User();
        user.setName(dto.getName());
        user.setEmail(dto.getEmail());
        return userRepository.save(user);
    }

    public User findUserById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("User not found with id " + id));
    }

    public void deleteUser(Long id) {
        userRepository.deleteById(id);
    }

    // ... 其他更新方法
}
最后，在 UserController 中调用这些服务方法，并连接到对应的 HTTP 端点。

接口文档
最后，一个专业的后端服务必须有清晰的接口文档。我们可以使用 SpringDoc OpenAPI (集成了 Swagger UI) 来自动生成交互式 API 文档。

安装依赖
在 pom.xml 中添加依赖：

XML

<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.5.0</version>
</dependency>
运行
重新启动应用。就是这么简单！Spring Boot 的自动配置会为你搞定一切。现在访问 http://localhost:8080/swagger-ui.html，你就能看到一个漂亮的、可交互的 API 文档页面了。

添加描述信息
为了让文档更清晰，我们可以使用注解来添加描述。

Java

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

@Tag(name = "用户管理", description = "用户相关的所有API")
@RestController
@RequestMapping("/user")
public class UserController {

    // ...

    @Operation(summary = "根据ID查找用户", description = "返回单个用户的详细信息")
    @GetMapping("/{id}")
    public User findOne(@PathVariable Long id) {
        // ...
    }
}
刷新 Swagger 页面，你会看到这些描述信息已经更新上去了。

至此，我们已经从零开始，循序渐进地学习了 Spring Boot 的核心概念，并搭建起一个包含 Web 层、业务逻辑层、数据访问层以及 API 文档的完整后端应用。这仅仅是一个开始，Spring Boot 的世界还有更多强大的功能等待你去探索。