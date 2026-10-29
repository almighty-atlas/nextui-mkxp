/* SPDX-License-Identifier: MIT
 * Original game-free video spike. See LICENSE in this directory.
 * A completed draw loop is NOT a physical-display/NextUI PASS.
 */
#define _POSIX_C_SOURCE 200809L
#include <SDL2/SDL.h>
#include <GLES2/gl2.h>
#include <EGL/egl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

#define RUN_MS 5000u
#define MAX_FRAMES 625u
static volatile sig_atomic_t stopping;
static void stop_requested(int signo) { (void)signo; stopping = 1; }
static void stage(const char *name, int code) {
    printf("RMXP_VIDEO stage=%s code=%d\n", name, code);
}
/* Fixed-size single-line strings; never log SDL errors, env or filesystem paths. */
static void metadata(const char *key, const char *value) {
    char text[97];
    size_t i = 0;
    if (!value) value = "UNKNOWN";
    while (i < sizeof(text)-1 && value[i]) {
        unsigned char c = (unsigned char)value[i];
        text[i] = (c >= 32 && c <= 126) ? (char)c : '?';
        i++;
    }
    text[i] = '\0';
    printf("RMXP_VIDEO %s=%s\n", key, text);
}
static GLuint shader(GLenum type, const char *source) {
    GLuint object = glCreateShader(type);
    GLint ok = GL_FALSE;
    if (!object) return 0;
    glShaderSource(object, 1, &source, NULL);
    glCompileShader(object);
    glGetShaderiv(object, GL_COMPILE_STATUS, &ok);
    if (!ok) { glDeleteShader(object); return 0; }
    return object;
}

int main(void) {
    static const char vertex_source[] =
        "attribute vec2 position; attribute vec3 color; uniform float shift;"
        "varying vec3 tint; void main(){tint=color;"
        "gl_Position=vec4(position+vec2(shift,0.0),0.0,1.0);}";
    static const char fragment_source[] =
        "precision mediump float; varying vec3 tint;"
        "void main(){gl_FragColor=vec4(tint,1.0);}";
    static const GLfloat vertices[] = {
         0.0f, 0.6f, 1.0f,0.1f,0.1f,
        -0.5f,-0.5f, 0.1f,1.0f,0.1f,
         0.5f,-0.5f, 0.1f,0.1f,1.0f
    };
    SDL_Window *window = NULL;
    SDL_GLContext context = NULL;
    SDL_version compiled, linked;
    GLuint vs=0, fs=0, program=0, buffer=0;
    GLint ok=GL_FALSE, shift=-1;
    int rc=10, initialized=0, width=0, height=0;
    unsigned frames=0;
    Uint32 started=0, elapsed=0;
    struct sigaction action;
    const char *driver, *renderer, *version;
    EGLDisplay display;
    memset(&action, 0, sizeof(action));
    action.sa_handler = stop_requested;
    sigemptyset(&action.sa_mask);
    setvbuf(stdout, NULL, _IONBF, 0);
    stage("start", 0);
    if ((SDL_getenv("SSH_CONNECTION") && *SDL_getenv("SSH_CONNECTION")) ||
        (SDL_getenv("SSH_CLIENT") && *SDL_getenv("SSH_CLIENT")) ||
        (SDL_getenv("SSH_TTY") && *SDL_getenv("SSH_TTY"))) {
        rc=31; stage("ssh_refused",rc); goto done;
    }
    SDL_VERSION(&compiled);
    SDL_GetVersion(&linked);
    printf("RMXP_VIDEO sdl_compiled=%u.%u.%u sdl_linked=%u.%u.%u\n",
           compiled.major,compiled.minor,compiled.patch,
           linked.major,linked.minor,linked.patch);
    if (sigaction(SIGTERM,&action,NULL) || sigaction(SIGINT,&action,NULL)) goto done;
    /* No driver override/fallback: require the normal NextUI Mali environment. */
    driver = SDL_getenv("SDL_VIDEODRIVER");
    if (!driver || strcmp(driver,"mali")) { rc=11; stage("backend_hint",rc); goto done; }
    if (SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER) != 0) { rc=12; stage("sdl_init",rc); goto done; }
    initialized=1;
    /* SDL may install its own handlers; restore our flag-only handlers. */
    if (sigaction(SIGTERM,&action,NULL) || sigaction(SIGINT,&action,NULL)) goto done;
    driver = SDL_GetCurrentVideoDriver();
    metadata("sdl_driver",driver);
    if (!driver || strcmp(driver,"mali")) { rc=13; stage("backend_actual",rc); goto done; }
    stage("sdl_ready",0);
    if (stopping) { rc=30; goto done; }
    if (SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES) ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2) ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0) ||
        SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER,1)) { rc=14; stage("attributes",rc); goto done; }
    window=SDL_CreateWindow("RMXP video test",SDL_WINDOWPOS_UNDEFINED,SDL_WINDOWPOS_UNDEFINED,
                            640,480,SDL_WINDOW_OPENGL|SDL_WINDOW_SHOWN);
    if (!window) { rc=15; stage("window",rc); goto done; }
    context=SDL_GL_CreateContext(window);
    if (!context) { rc=16; stage("context",rc); goto done; }
    if (SDL_GL_MakeCurrent(window,context)) { rc=17; stage("make_current",rc); goto done; }
    stage("context_ready",0);
    renderer=(const char *)glGetString(GL_RENDERER);
    version=(const char *)glGetString(GL_VERSION);
    if (!renderer || !*renderer || !version || strncmp(version,"OpenGL ES ",10) ||
        version[10]<'2' || version[10]>'9') { rc=19; stage("gles_identity",rc); goto done; }
    metadata("gl_vendor",(const char *)glGetString(GL_VENDOR));
    metadata("gl_renderer",(const char *)glGetString(GL_RENDERER));
    metadata("gl_version",(const char *)glGetString(GL_VERSION));
    metadata("glsl_version",(const char *)glGetString(GL_SHADING_LANGUAGE_VERSION));
    display=eglGetCurrentDisplay();
    if (display==EGL_NO_DISPLAY) { rc=18; stage("egl_display",rc); goto done; }
    metadata("egl_vendor",eglQueryString(display,EGL_VENDOR));
    metadata("egl_version",eglQueryString(display,EGL_VERSION));
    /* Vsync is not required. Request nonblocking swaps; a driver can still stall. */
    if (SDL_GL_SetSwapInterval(0)) stage("swap_interval_unavailable",0);
    vs=shader(GL_VERTEX_SHADER,vertex_source);
    fs=shader(GL_FRAGMENT_SHADER,fragment_source);
    if (!vs || !fs) { rc=20; stage("shader",rc); goto done; }
    program=glCreateProgram();
    if (!program) { rc=21; stage("program",rc); goto done; }
    glAttachShader(program,vs); glAttachShader(program,fs);
    glBindAttribLocation(program,0,"position"); glBindAttribLocation(program,1,"color");
    glLinkProgram(program); glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if (!ok) { rc=21; stage("program",rc); goto done; }
    shift=glGetUniformLocation(program,"shift");
    if (shift<0) { rc=22; stage("uniform",rc); goto done; }
    glGenBuffers(1,&buffer);
    if (!buffer) { rc=23; stage("buffer",rc); goto done; }
    glBindBuffer(GL_ARRAY_BUFFER,buffer);
    glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),vertices,GL_STATIC_DRAW);
    glUseProgram(program);
    glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,5*sizeof(GLfloat),(void *)0);
    glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,5*sizeof(GLfloat),(void *)(2*sizeof(GLfloat)));
    glEnableVertexAttribArray(0); glEnableVertexAttribArray(1);
    SDL_GL_GetDrawableSize(window,&width,&height);
    if (width<=0 || height<=0 || glGetError()!=GL_NO_ERROR) { rc=24; stage("draw_setup",rc); goto done; }
    glViewport(0,0,width,height);
    stage("draw_begin",0);
    started=SDL_GetTicks();
    while (frames<MAX_FRAMES && !stopping) {
        SDL_Event event;
        /* One event per frame: even an event flood cannot starve the deadline. */
        if (SDL_PollEvent(&event) && event.type==SDL_QUIT) stopping=1;
        elapsed=(Uint32)(SDL_GetTicks()-started); /* wrap-safe over five seconds */
        if (stopping || elapsed>=RUN_MS) break;
        /* Triangle-wave horizontal movement; no assets, libm or per-frame logs. */
        {
            float phase=(float)(elapsed%2000u)/1000.0f;
            float offset=(phase<1.0f ? phase : 2.0f-phase)*0.5f-0.25f;
            glUniform1f(shift,offset);
        }
        glClearColor(0.04f,0.04f,0.08f,1.0f); glClear(GL_COLOR_BUFFER_BIT);
        glDrawArrays(GL_TRIANGLES,0,3);
        if (glGetError()!=GL_NO_ERROR) { rc=25; stage("draw",rc); goto done; }
        SDL_ClearError();
        SDL_GL_SwapWindow(window);
        if (*SDL_GetError()) { rc=27; stage("swap",rc); goto done; }
        frames++;
        SDL_Delay(8);
    }
    elapsed=(Uint32)(SDL_GetTicks()-started);
    if (stopping) rc=30;
    else if (elapsed<RUN_MS || frames<2) rc=26; /* stalled clock / no animated run */
    else rc=0;
    printf("RMXP_VIDEO stage=draw_end code=%d frames=%u elapsed_ms=%u\n",rc,frames,elapsed);
done:
    if (context) {
        if (buffer) glDeleteBuffers(1,&buffer);
        if (program) glDeleteProgram(program);
        if (vs) glDeleteShader(vs);
        if (fs) glDeleteShader(fs);
        SDL_GL_DeleteContext(context);
    }
    if (window) SDL_DestroyWindow(window);
    /* Also shut down a partially failed SDL initialization. */
    if (initialized || rc==12) SDL_Quit();
    stage("cleanup_complete",rc);
    stage("exit_owner_verification_required",rc);
    return rc;
}
