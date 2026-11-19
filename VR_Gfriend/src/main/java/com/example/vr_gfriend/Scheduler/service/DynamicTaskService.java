package com.example.vr_gfriend.Scheduler.service;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.support.CronTrigger;
import org.springframework.stereotype.Service;

import java.time.ZoneId;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;

@Service
public class DynamicTaskService {
    private static final Duration MINIMUM_GENERATION_INTERVAL = Duration.ofMinutes(1);
    private final TaskScheduler scheduler;
    private final DailyBriefingService briefings;
    private final ZoneId timezone;
    private final Map<String, ScheduledFuture<?>> tasks = new HashMap<>();

    public DynamicTaskService(TaskScheduler scheduler, DailyBriefingService briefings,
                              @Value("${ga.briefing.timezone}") String timezone) {
        this.scheduler = scheduler;
        this.briefings = briefings;
        this.timezone = ZoneId.of(timezone);
    }

    public synchronized void updateTask(UserAlarmProfileDTO settings) {
        String userId = settings.getUserId();
        ScheduledFuture<?> replacement = settings.isEnabled()
                ? scheduler.schedule(new ScheduledBriefing(settings),
                        new CronTrigger(settings.getCronExpression(), timezone))
                : null;
        ScheduledFuture<?> previous = replacement == null ? tasks.remove(userId) : tasks.put(userId, replacement);
        if (previous != null) {
            previous.cancel(false);
        }
    }

    private final class ScheduledBriefing implements Runnable {
        private final UserAlarmProfileDTO settings;
        private Instant nextGeneration = Instant.MIN;

        private ScheduledBriefing(UserAlarmProfileDTO settings) {
            this.settings = settings;
        }

        @Override
        public void run() {
            Instant now = scheduler.getClock().instant();
            if (now.isBefore(nextGeneration)) {
                return;
            }
            nextGeneration = now.plus(MINIMUM_GENERATION_INTERVAL);
            briefings.triggerCustomBriefing(settings);
        }
    }
}
