package com.example.vr_gfriend.Scheduler.DTO;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class UserAlarmProfileDTO {
    @JsonIgnore
    private String userId;
    @Size(max = 100)
    private String city;
    @Size(max = 128)
    private String cronExpression;
    @Size(max = 1024)
    private String scheduleFilePath;
    private boolean enabled;
}
