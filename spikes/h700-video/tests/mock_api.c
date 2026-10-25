/* SPDX-License-Identifier: MIT
 * Original simulated API. Never links/loads SDL/GL, opens a display or a node.
 */
#include <SDL2/SDL.h>
#include <GLES2/gl2.h>
#include <EGL/egl.h>
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned ticks,frames,draws,deleted_shaders;
static int window_live,context_live,buffer_live,program_live,init_called,attributes;
static int have_offset,offset_changed;
static float first_offset;
static SDL_Window window;
static int scenario(const char *s) { const char *v=getenv("MOCK_CASE"); return v && !strcmp(v,s); }
void SDL_GetVersion(SDL_version *v) {
    if(scenario("noisy")) { unsigned i; for(i=0;i<100000;i++) puts("MOCK_NOISE_0123456789"); }
    SDL_VERSION(v);
}
char *SDL_getenv(const char *k) { return getenv(k); }
int SDL_Init(Uint32 flags) { assert(flags==(SDL_INIT_VIDEO|SDL_INIT_TIMER)); init_called=1; if(scenario("wrap")) ticks=UINT32_MAX-100; return scenario("init_fail")?-1:0; }
const char *SDL_GetCurrentVideoDriver(void) { return scenario("wrong_driver")?"kmsdrm":"mali"; }
int SDL_GL_SetAttribute(int k,int v) {
    assert(!window_live);
    if (k==SDL_GL_CONTEXT_PROFILE_MASK) assert(v==SDL_GL_CONTEXT_PROFILE_ES);
    if (k==SDL_GL_CONTEXT_MAJOR_VERSION) assert(v==2);
    attributes++;
    return scenario("attribute_fail")?-1:0;
}
SDL_Window *SDL_CreateWindow(const char *s,int x,int y,int w,int h,Uint32 flags) {
    (void)s;(void)x;(void)y; assert(w==640 && h==480 && attributes==4);
    assert(flags==(SDL_WINDOW_OPENGL|SDL_WINDOW_SHOWN));
    if(scenario("window_fail")) return NULL;
    window_live=1; return &window;
}
SDL_GLContext SDL_GL_CreateContext(SDL_Window *w) {
    assert(w==&window);
    if(scenario("context_fail")) return NULL;
    context_live=1; return &window;
}
int SDL_GL_MakeCurrent(SDL_Window *w,SDL_GLContext c) { assert(w && c);return scenario("current_fail")?-1:0; }
int SDL_GL_SetSwapInterval(int v) { assert(v==0);return 0; }
void SDL_GL_GetDrawableSize(SDL_Window *w,int *x,int *y) { assert(w);*x=scenario("bad_size")?0:640;*y=480; }
Uint32 SDL_GetTicks(void) { return scenario("clock_stuck")?0:ticks; }
int SDL_PollEvent(SDL_Event *e) { if(scenario("event_flood")){e->type=0;return 1;} if(scenario("quit") && frames==2){e->type=SDL_QUIT;return 1;}return 0; }
void SDL_GL_SwapWindow(SDL_Window *w) {
    assert(w && draws==frames+1);frames++;
    if(scenario("term") && frames==2) raise(SIGTERM);
    if(scenario("int") && frames==2) raise(SIGINT);
}
void SDL_ClearError(void) {}
const char *SDL_GetError(void) { return scenario("swap_fail") && frames?"mock failure":""; }
void SDL_Delay(Uint32 ms) { ticks+=ms; }
void SDL_GL_DeleteContext(SDL_GLContext c) { assert(c && !buffer_live && !program_live); context_live=0; }
void SDL_DestroyWindow(SDL_Window *w) { assert(w && !context_live);window_live=0; }
void SDL_Quit(void) {
    assert(init_called && !window_live && !context_live && !buffer_live && !program_live);
    if(frames>2 && !scenario("clock_stuck")) assert(offset_changed);
    printf("MOCK cleanup=ok swaps=%u draws=%u shaders_deleted=%u\n",frames,draws,deleted_shaders);
}
GLuint glCreateShader(GLenum t) { assert(context_live);return t; }
void glShaderSource(GLuint s,int n,const char *const *text,const int *len) { (void)s;(void)len;assert(n==1 && strstr(*text,"void main()")); }
void glCompileShader(GLuint s) { assert(s); }
void glGetShaderiv(GLuint s,GLenum p,GLint *ok) { (void)s;(void)p;*ok=!scenario("shader_fail"); }
void glDeleteShader(GLuint s) { assert(s);deleted_shaders++; }
const unsigned char *glGetString(GLenum p) {
    if(p==GL_VERSION) return (const unsigned char *)(scenario("bad_gl")?"OpenGL 2.0":"OpenGL ES 2.0 MOCK");
    return (const unsigned char *)(scenario("long_metadata")?"line\ncontrol\001 with a long mock driver name 12345678901234567890123456789012345678901234567890123456789012345678901234567890":"MOCK_NOT_REAL_GPU");
}
EGLDisplay eglGetCurrentDisplay(void) { return scenario("egl_fail")?EGL_NO_DISPLAY:&window; }
const char *eglQueryString(EGLDisplay d,int k) { (void)k;assert(d);return "MOCK_NOT_REAL_EGL"; }
GLuint glCreateProgram(void) { program_live=1;return 42; }
void glAttachShader(GLuint p,GLuint s) { assert(p && s); }
void glBindAttribLocation(GLuint p,GLuint i,const char *name) { assert(p && i<2 && name); }
void glLinkProgram(GLuint p) { assert(p); }
void glGetProgramiv(GLuint p,GLenum k,GLint *ok) { (void)p;(void)k;*ok=!scenario("link_fail"); }
GLint glGetUniformLocation(GLuint p,const char *s) { assert(p && !strcmp(s,"shift"));return scenario("uniform_fail")?-1:0; }
void glGenBuffers(int n,GLuint *b) { assert(n==1); *b=scenario("buffer_fail")?0:43;buffer_live=(*b!=0); }
void glBindBuffer(GLenum t,GLuint b) { assert(t==GL_ARRAY_BUFFER && b); }
void glBufferData(GLenum t,ptrdiff_t n,const void *data,GLenum usage) { assert(t==GL_ARRAY_BUFFER && n==15*sizeof(GLfloat) && data && usage==GL_STATIC_DRAW); }
void glUseProgram(GLuint p) { assert(p); }
void glVertexAttribPointer(GLuint i,int n,GLenum t,unsigned char norm,int stride,const void *ptr) { (void)ptr;assert(i<2 && (n==2||n==3) && t==GL_FLOAT && !norm && stride==5*sizeof(GLfloat)); }
void glEnableVertexAttribArray(GLuint i) { assert(i<2); }
GLenum glGetError(void) { return scenario("draw_fail") && draws?1:GL_NO_ERROR; }
void glViewport(int x,int y,int w,int h) { assert(!x && !y && w==640 && h==480); }
void glUniform1f(GLint loc,GLfloat offset) { assert(loc==0);if(!have_offset){first_offset=offset;have_offset=1;}else if(offset!=first_offset)offset_changed=1; }
void glClearColor(GLfloat r,GLfloat g,GLfloat b,GLfloat a) { (void)r;(void)g;(void)b;assert(a==1); }
void glClear(GLenum mask) { assert(mask==GL_COLOR_BUFFER_BIT); }
void glDrawArrays(GLenum mode,int first,int count) { assert(mode==GL_TRIANGLES && first==0 && count==3 && buffer_live && program_live);draws++; }
void glDeleteBuffers(int n,const GLuint *b) { assert(n==1 && *b);buffer_live=0; }
void glDeleteProgram(GLuint p) { assert(p);program_live=0; }
