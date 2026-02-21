# VR_Gfriend Login 实现说明

## 1. completeProfile 的 HttpServletRequest 参数分析

### 问题
在 `Usercontroller.java` 的 `completeProfile` 方法中：
```java
public Result completeProfile(@Valid @RequestBody Register_step2 dto, HttpServletRequest request)
```

### 答案
**这个 `request` 参数是冗余的，已被删除。**

#### 原因：
- 方法体内部没有使用 `request` 对象
- userId 是通过 `UserContext.getUserId()` 从 ThreadLocal 获取的
- ThreadLocal 中的 userId 由 `JwtInterceptor` 在请求预处理时从 JWT token 中解析并存储

#### 修改后：
```java
public Result completeProfile(@Valid @RequestBody Register_step2 dto) {
    String userId = UserContext.getUserId(); // 来自拦截器的 ThreadLocal
    boolean s = service.updateUserProfile(userId, dto);
    return s ? Result.success("画像填写完成，欢迎进入 AI 世界！") : Result.error("更新失败");
}
```

---

## 2. JwtInterceptor 全流程分析

### 流程图
```
HTTP 请求
    ↓
WebConfig (拦截配置)
    ↓
JwtInterceptor.preHandle() ← 从 Header 获取 Authorization token
    ↓
验证 token 有效性
    ├─ 有效 → 解析 userId → 存入 UserContext (ThreadLocal) → 继续执行
    └─ 无效/不存在 → 返回 401 Unauthorized → 拦截请求
    ↓
Controller 执行 (通过 UserContext.getUserId() 获取用户ID)
    ↓
JwtInterceptor.afterCompletion() ← 清理 ThreadLocal
    ↓
响应返回
```

### 详细说明

#### 步骤 1：拦截器配置 (`WebConfig.java`)
```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Autowired
    private JwtInterceptor jwtInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtInterceptor)
                .addPathPatterns("/**")  // 拦截所有路径
                .excludePathPatterns(
                    "/admin/user/register",  // 放行注册
                    "/admin/user/login",     // 放行登录
                    "/api/**"                // 放行API路径
                );
    }
}
```

**重点**：
- ✅ `/admin/user/complete-profile` 会被拦截（需要 token）
- ✅ `/admin/user/login` 不会被拦截（登录接口）
- ✅ `/admin/user/register` 不会被拦截（注册接口）

#### 步骤 2：预处理 (`JwtInterceptor.preHandle()`)
```java
@Override
public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
    // 1. 从 Header 获取 Token
    String token = request.getHeader("Authorization");

    // 2. 判定并解析
    if (token != null && !token.isEmpty()) {
        try {
            // 解析 token 获取 userId
            String userId = jwtUtils.getUserIdFromToken(token);
            
            // 存入 ThreadLocal
            UserContext.setUserId(userId);
            return true;  // 继续执行
        } catch (Exception e) {
            // Token 无效
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;  // 拦截请求
        }
    }

    // 无 Token 访问受限接口
    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
    return false;
}
```

#### 步骤 3：后处理 (`JwtInterceptor.afterCompletion()`)
```java
@Override
public void afterCompletion(HttpServletRequest request, HttpServletResponse response, 
                           Object handler, Exception ex) {
    // 必须清理，否则在线程池环境下会引起内存泄漏或数据污染
    UserContext.remove();
}
```

### 结论
**✅ 是的，JwtInterceptor 全流程都已正确配置并运行！**

所有需要认证的接口（除了登录、注册、API路径）都会经过以下流程：
1. 检查 Authorization header
2. 验证 token 有效性
3. 解析 userId 并存入 ThreadLocal
4. 业务逻辑执行
5. 清理 ThreadLocal

---

## 3. Login 代码实现

### 新增功能
已完成以下登录相关代码：

#### 3.1 Controller 层 (`Usercontroller.java`)
```java
@PostMapping("/login")
public Result login(@RequestBody @Valid LoginDTO dto) {
    String token = service.loginUser(dto);
    return token != null 
        ? Result.success(token) 
        : Result.error("登录失败，用户名或密码错误");
}
```

#### 3.2 Service 接口 (`Userservice.java`)
```java
public interface Userservice {
    String registerUser(Register_Step1 user);
    String loginUser(LoginDTO dto);  // 新增
    boolean updateUserProfile(String userId, Register_step2 dto);
    // ... 其他方法
}
```

#### 3.3 Service 实现 (`UserserviceImpl.java`)
```java
@Override
public String loginUser(LoginDTO dto) {
    User user = null;
    
    // 根据邮箱或手机号查询用户
    if (dto.getEmail() != null && !dto.getEmail().isEmpty()) {
        user = userMapper.selectByEmail(dto.getEmail());
    } else if (dto.getPhone() != null && !dto.getPhone().isEmpty()) {
        user = userMapper.selectByPhone(dto.getPhone());
    }
    
    // 验证用户是否存在
    if (user == null) {
        return null; // 用户不存在
    }
    
    // 验证密码
    if (!user.getPasswordHash().equals(dto.getPassword())) {
        return null; // 密码错误
    }
    
    // 验证用户状态
    if (user.getStatus() != 1) {
        return null; // 用户被禁用
    }
    
    // 生成并返回 JWT token
    return jwtUtils.createToken(user.getUserId());
}
```

#### 3.4 Mapper 层 (`UserMapper.java`)
```java
@Mapper
public interface UserMapper extends BaseMapper<User> {
    User selectByEmail(String email);  // 新增
    User selectByPhone(String phone);  // 新增
    // ... 其他方法
}
```

#### 3.5 Mapper XML (`UserMapper.xml`)
```xml
<select id="selectByEmail" resultType="com.example.vr_gfriend.user.entity.User">
    SELECT
        id, user_id, email, phone, password_hash,
        register_type, register_stage, status,
        username, nickname, avatar_url, gender, birthday,
        created_at, updated_at
    FROM user
    WHERE email = #{email}
</select>

<select id="selectByPhone" resultType="com.example.vr_gfriend.user.entity.User">
    SELECT
        id, user_id, email, phone, password_hash,
        register_type, register_stage, status,
        username, nickname, avatar_url, gender, birthday,
        created_at, updated_at
    FROM user
    WHERE phone = #{phone}
</select>
```

---

## 4. 登录流程示例

### 前端调用示例
```javascript
// 邮箱登录
fetch('http://localhost:8080/admin/user/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password123'
    })
})
.then(response => response.json())
.then(data => {
    if (data.code === 200) {
        // 登录成功，保存 token
        localStorage.setItem('token', data.data);
    } else {
        console.error('登录失败:', data.message);
    }
});

// 手机号登录
fetch('http://localhost:8080/admin/user/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        phone: '13800138000',
        password: 'password123'
    })
})
.then(response => response.json())
.then(data => {
    if (data.code === 200) {
        localStorage.setItem('token', data.data);
    }
});
```

### 后续请求携带 Token
```javascript
fetch('http://localhost:8080/admin/user/complete-profile', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': localStorage.getItem('token')  // 携带 token
    },
    body: JSON.stringify({
        username: 'testuser',
        nickname: '测试用户',
        gender: 0,
        birthday: '1995-01-01',
        avatarUrl: 'https://example.com/avatar.jpg'
    })
});
```

---

## 5. 安全性建议

### ⚠️ 当前实现的问题
1. **密码明文存储**：当前密码直接以明文形式存储在数据库中
2. **密码明文比较**：登录时直接比较明文密码

### 🔒 推荐改进方案

#### 方案 1：使用 Spring Security + BCrypt（推荐）

1. 添加依赖到 `pom.xml`：
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

2. 创建密码编码器配置：
```java
@Configuration
public class SecurityConfig {
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

3. 修改注册逻辑：
```java
@Autowired
private PasswordEncoder passwordEncoder;

public String registerUser(Register_Step1 dto) {
    // ...
    user.setPasswordHash(passwordEncoder.encode(dto.getPassword())); // 加密
    // ...
}
```

4. 修改登录验证：
```java
// 验证密码
if (!passwordEncoder.matches(dto.getPassword(), user.getPasswordHash())) {
    return null; // 密码错误
}
```

#### 方案 2：手动实现 BCrypt（轻量级）

添加依赖：
```xml
<dependency>
    <groupId>org.mindrot</groupId>
    <artifactId>jbcrypt</artifactId>
    <version>0.4</version>
</dependency>
```

使用示例：
```java
import org.mindrot.jbcrypt.BCrypt;

// 注册时
String hashedPassword = BCrypt.hashpw(dto.getPassword(), BCrypt.gensalt());

// 登录验证
if (!BCrypt.checkpw(dto.getPassword(), user.getPasswordHash())) {
    return null;
}
```

---

## 6. 测试建议

### 测试用例
1. **正常登录**：正确的邮箱/手机号 + 正确的密码
2. **错误密码**：正确的邮箱/手机号 + 错误的密码
3. **不存在的用户**：不存在的邮箱/手机号
4. **被禁用的用户**：status != 1 的用户
5. **Token 有效性**：登录后使用返回的 token 访问受保护接口
6. **Token 过期**：等待 12 小时后测试 token 是否过期

### Postman 测试示例

#### 1. 注册用户
```
POST http://localhost:8080/admin/user/register
Content-Type: application/json

{
    "email": "test@example.com",
    "phone": "13800138000",
    "password": "password123"
}
```

#### 2. 登录（邮箱）
```
POST http://localhost:8080/admin/user/login
Content-Type: application/json

{
    "email": "test@example.com",
    "password": "password123"
}
```

#### 3. 完善资料（需要 token）
```
POST http://localhost:8080/admin/user/complete-profile
Content-Type: application/json
Authorization: <从登录响应中获取的 token>

{
    "username": "testuser",
    "nickname": "测试用户",
    "gender": 0,
    "birthday": "1995-01-01",
    "avatarUrl": "https://example.com/avatar.jpg"
}
```

---

## 7. 常见问题

### Q1: 为什么 completeProfile 不需要 HttpServletRequest 参数？
**A**: 因为 userId 已经通过 `JwtInterceptor` 解析并存储在 `UserContext` (ThreadLocal) 中，可以直接通过 `UserContext.getUserId()` 获取，不需要从 request 中提取。

### Q2: JwtInterceptor 会拦截所有接口吗？
**A**: 不会。配置了排除路径：
- `/admin/user/register` - 注册接口
- `/admin/user/login` - 登录接口
- `/api/**` - 所有 API 路径

### Q3: 如何添加新的不需要认证的接口？
**A**: 在 `WebConfig.java` 的 `excludePathPatterns()` 中添加路径即可。

### Q4: Token 存储在哪里？
**A**: 
- 后端：不存储，采用无状态设计
- 前端：建议存储在 `localStorage` 或 `sessionStorage`
- 传输：通过 HTTP Header 的 `Authorization` 字段传递

### Q5: 登录后如何访问受保护的接口？
**A**: 在所有请求的 HTTP Header 中添加：
```
Authorization: <登录时返回的 token>
```

---

## 总结

✅ 已完成的功能：
1. 修复了 `completeProfile` 方法的冗余参数
2. 分析了 JwtInterceptor 的完整流程
3. 实现了完整的登录功能（支持邮箱和手机号登录）
4. 添加了必要的数据库查询方法
5. 实现了 JWT token 生成和验证

⚠️ 需要改进的地方：
1. 密码加密（建议使用 BCrypt）
2. 添加登录失败次数限制
3. 添加登录日志记录
4. Token 刷新机制
5. 异常处理优化

📝 下一步建议：
1. 集成 Spring Security 和 BCrypt 进行密码加密
2. 添加单元测试
3. 添加接口文档（Swagger）
4. 实现登录日志功能
