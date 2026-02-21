package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.*;
import lombok.Data;
import org.hibernate.validator.constraints.Range;

import java.time.LocalDate;

@Data
public class Register_Step1 {
    private String userId;
    @NotBlank(message = "邮箱不能为空或者都是空格")
    @Email(message = "邮箱格式不正确")
    private String email;
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    @NotBlank(message = "电话号码不能为空或者都是空格")
    private String phone;
    @NotBlank(message = "密码不能为空或者都是空格")
    @Size(min = 6, max = 20, message = "密码长度必须在 6 到 20 位之间")
    private String password;
    /*
    分割线
     */

}
