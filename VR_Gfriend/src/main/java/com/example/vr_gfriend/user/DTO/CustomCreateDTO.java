package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

// 2. 自定义创建 DTO (当用户觉得模板不好时使用)
@Data
public class CustomCreateDTO {
    @NotBlank(message = "AI昵称不能为空")
    @Size(max = 100)
    private String aiName;

    @Size(max = 30)
    private List<@NotBlank @Size(max = 80) String> personalityTags;
    @Size(max = 30)
    private List<@NotBlank @Size(max = 80) String> interests;

    // 用户可以直接写一段描述，或者由后端根据标签生成
    @Size(max = 4000)
    private String description;
}
