package com.example.vr_gfriend.user.DTO;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * AI 模板展示对象 (DTO/VO)
 * 对应 ai_templates.json 的结构
 */
@Data
public class AITemplate {
    private String templateId;    // "1"
    private String name;          // "夏心玲"
    private List<String> tags;    // "温柔,耐心"
    private String interests;     // "烹饪,记录生活"

    // 注意：initPrompt 可以传给前端，也可以选择不传（如果不希望用户看到底层的 Prompt）
    @JsonProperty(access = JsonProperty.Access.WRITE_ONLY)
    private String initPrompt;
}
