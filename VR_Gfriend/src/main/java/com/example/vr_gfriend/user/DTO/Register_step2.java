package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Size;
import lombok.Data;
import org.hibernate.validator.constraints.Range;

import java.time.LocalDate;

@Data
public class Register_step2 {
    @NotBlank(message = "用户名不能为空")
    @Size(max = 50, message = "用户名太长啦，建议50字以内")
    private String username;

    @NotBlank(message = "起个好听的昵称，能让称呼更亲昵哦")
    @Size(max = 100)
    private String nickname;

    @Size(max = 2048)
    private String avatarUrl;

    @NotNull(message = "请选择您的性别")
    @Range(min = 0, max = 3, message = "性别选择超出范围")
    private Integer gender; // 0未知 1男 2女 3其他

    @NotNull(message = "生日是我们的重要纪念日，请填写哦")
    @Past(message = "生日必须是过去的时间点")
    private LocalDate birthday;

}
