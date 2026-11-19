package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class Register_Step1 {
    @Email(message = "邮箱格式不正确")
    @Size(max = 255)
    private String email;
    @Pattern(regexp = "^(?:1[3-9]\\d{9})?$", message = "手机号格式不正确")
    private String phone;
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 20, message = "密码长度必须在 6 到 20 位之间")
    private String password;

    @AssertTrue(message = "请填写邮箱或手机号")
    public boolean isContactProvided() {
        return email != null && !email.isBlank() || phone != null && !phone.isBlank();
    }
}
