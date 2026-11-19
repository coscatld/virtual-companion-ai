package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

// 1. 快捷应用模板 DTO
@Data
public class TemplateSelectDTO {
    @NotBlank(message = "模板ID不能为空")
    private String templateId;

    // 允许用户微调名字，如果为空则使用模板默认名
    @Size(max = 100)
    private String aiName;
}
