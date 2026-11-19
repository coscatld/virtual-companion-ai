package com.example.vr_gfriend.Scheduler;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.Scheduler.service.DailyBriefingService;
import com.example.vr_gfriend.Scheduler.service.DailyBriefingService.Briefing;
import com.example.vr_gfriend.Scheduler.service.UserAlarmService;
import com.example.vr_gfriend.agent.InferenceQuota;
import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.config.Result;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/briefing")
@RequiredArgsConstructor
public class DailyBriefingController {
    private final DailyBriefingService dailyBriefing;
    private final UserAlarmService userAlarms;
    private final InferenceQuota quota;

    @GetMapping("/settings")
    public Result<UserAlarmProfileDTO> settings() {
        return Result.success(userAlarms.findSettings(UserContext.getUserId()));
    }

    @GetMapping("/latest")
    public Result<Briefing> latest() {
        return Result.success(dailyBriefing.latest(UserContext.getUserId()));
    }

    @PostMapping(value = "/set", produces = MediaType.TEXT_PLAIN_VALUE)
    public String setAlarm(@Valid @RequestBody UserAlarmProfileDTO dto) {
        dto.setUserId(UserContext.getUserId());
        userAlarms.saveAndSchedule(dto);
        return dto.isEnabled() ? "每日早报已开启。" : "每日早报已关闭。";
    }

    @GetMapping(value = "/test", produces = MediaType.TEXT_PLAIN_VALUE)
    public Flux<String> testBriefing() {
        String userId = UserContext.getUserId();
        quota.claimText(userId);
        return dailyBriefing.generateDailyBriefing(userId, userAlarms.findSettings(userId));
    }

    @GetMapping(value = "/test/{userId}", produces = MediaType.TEXT_PLAIN_VALUE)
    public Flux<String> testLegacyBriefing(@PathVariable String userId) {
        if (!userId.equals(UserContext.getUserId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只能预览当前账号的早报");
        }
        return testBriefing();
    }
}
