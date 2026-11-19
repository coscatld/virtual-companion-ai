package com.example.vr_gfriend;

import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.agent.AgentClientService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import reactor.core.publisher.Flux;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.startsWith;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties = {
        "spring.datasource.url=jdbc:h2:mem:ga;MODE=MySQL;NON_KEYWORDS=USER;DB_CLOSE_DELAY=-1",
        "spring.datasource.username=sa",
        "spring.datasource.password=",
        "spring.sql.init.mode=always",
        "ga.internal-token=test-internal"
})
@AutoConfigureMockMvc
class VrGfriendApplicationTests {
    @Autowired private MockMvc mvc;
    @Autowired private ObjectMapper json;
    @Autowired private JdbcTemplate jdbc;
    @MockBean private AgentClientService agent;

    @Test
    void onboardingRestoresCompanionFromDatabaseAndKeepsPromptInternal() throws Exception {
        String authorization = register("onboarding@ga.test");
        mvc.perform(get("/admin/user/companion").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data").isEmpty());
        mvc.perform(get("/admin/user/me").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.registerStage").value(0));
        mvc.perform(post("/admin/user/complete-profile").header(HttpHeaders.AUTHORIZATION, authorization)
                        .contentType(MediaType.APPLICATION_JSON).content("""
                                {"username":"ga-user","nickname":"用户","gender":0,"birthday":"2000-01-01"}
                                """))
                .andExpect(status().isOk());
        mvc.perform(get("/admin/user/templates").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data[0].tags[0]").value("温柔"))
                .andExpect(jsonPath("$.data[0].initPrompt").doesNotExist());
        mvc.perform(post("/admin/user/use-template").header(HttpHeaders.AUTHORIZATION, authorization)
                        .contentType(MediaType.APPLICATION_JSON).content("""
                                {"templateId":"1","aiName":"小夏"}
                                """))
                .andExpect(status().isOk());
        mvc.perform(get("/admin/user/me").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.registerStage").value(2));
        mvc.perform(get("/admin/user/companion").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.name").value("小夏"))
                .andExpect(jsonPath("$.data.tags[0]").value("温柔"))
                .andExpect(jsonPath("$.data.interests[0]").value("烹饪"))
                .andExpect(jsonPath("$.data.systemPrompt").doesNotExist());
        mvc.perform(get("/internal/mobile/companion").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isForbidden());
        mvc.perform(get("/internal/mobile/companion").header(HttpHeaders.AUTHORIZATION, authorization)
                        .header("X-GA-Internal-Token", "test-internal"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.systemPrompt").value(containsString("小夏")))
                .andExpect(jsonPath("$.companionId").value("default"));
    }

    @Test
    void streamsMultilineDeltasAndTerminalEventAndIsolatesBriefingSettings() throws Exception {
        String authorization = register("streams@ga.test");
        String other = register("other@ga.test");
        String userId = jdbc.queryForObject("SELECT user_id FROM user WHERE email = ?", String.class, "streams@ga.test");
        assertNotNull(userId);
        when(agent.streamChat(eq(userId), anyString())).thenReturn(Flux.just(
                AgentProto.ChatResponse.newBuilder().setDelta("第一行\n第二行").build(),
                AgentProto.ChatResponse.newBuilder().setIsEnd(true).build()));
        var stream = mvc.perform(post("/api/chat/stream").header(HttpHeaders.AUTHORIZATION, authorization)
                        .accept(MediaType.TEXT_EVENT_STREAM).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"你好\"}"))
                .andExpect(request().asyncStarted()).andReturn();
        mvc.perform(asyncDispatch(stream)).andExpect(status().isOk())
                .andExpect(content().string(containsString("event:message\ndata:第一行\ndata:第二行\n\n")))
                .andExpect(content().string(containsString("event:done\ndata:ok\n\n")));

        mvc.perform(post("/api/briefing/set").header(HttpHeaders.AUTHORIZATION, authorization)
                        .contentType(MediaType.APPLICATION_JSON).content("""
                                {"city":"杭州","cronExpression":"08:15","enabled":true}
                                """))
                .andExpect(status().isOk());
        mvc.perform(get("/api/briefing/settings").header(HttpHeaders.AUTHORIZATION, authorization))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.city").value("杭州"))
                .andExpect(jsonPath("$.data.cronExpression").value("0 15 8 * * ?"));
        mvc.perform(get("/api/briefing/settings").header(HttpHeaders.AUTHORIZATION, other))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data").isEmpty());
        mvc.perform(get("/api/briefing/test/{userId}", userId).header(HttpHeaders.AUTHORIZATION, other))
                .andExpect(status().isForbidden());
        mvc.perform(post("/api/briefing/set").header(HttpHeaders.AUTHORIZATION, authorization)
                        .contentType(MediaType.APPLICATION_JSON).content("""
                                {"city":"杭州","cronExpression":"99:12","enabled":true}
                                """))
                .andExpect(status().isBadRequest());
    }

    @Test
    void migratesLegacyPasswordOnLogin() throws Exception {
        jdbc.update("""
                INSERT INTO user (user_id, email, password_hash, register_type, register_stage, status)
                VALUES ('legacy', 'legacy@ga.test', 'legacy123', 0, 0, 1)
                """);
        mvc.perform(post("/admin/user/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"legacy@ga.test\",\"password\":\"legacy123\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data").value(startsWith("ey")));
        String stored = jdbc.queryForObject("SELECT password_hash FROM user WHERE user_id = 'legacy'", String.class);
        org.junit.jupiter.api.Assertions.assertTrue(stored != null && stored.startsWith("$2"));
    }

    private String register(String email) throws Exception {
        String response = mvc.perform(post("/admin/user/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"test123456\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return "Bearer " + json.readTree(response).get("data").asText();
    }
}
