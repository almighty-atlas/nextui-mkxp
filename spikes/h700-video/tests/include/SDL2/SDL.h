/* SPDX-License-Identifier: MIT
 * Original mock declarations for tests, NOT SDL headers or an ABI substitute.
 */
#ifndef MOCK_SDL_H
#define MOCK_SDL_H
#include <stdint.h>
typedef uint32_t Uint32;
typedef struct SDL_Window { int placeholder; } SDL_Window;
typedef void *SDL_GLContext;
typedef struct { unsigned char major,minor,patch; } SDL_version;
typedef struct { unsigned type; } SDL_Event;
#define SDL_VERSION(v) ((v)->major=2,(v)->minor=28,(v)->patch=5)
#define SDL_INIT_VIDEO 1
#define SDL_INIT_TIMER 2
#define SDL_GL_CONTEXT_PROFILE_MASK 1
#define SDL_GL_CONTEXT_PROFILE_ES 2
#define SDL_GL_CONTEXT_MAJOR_VERSION 3
#define SDL_GL_CONTEXT_MINOR_VERSION 4
#define SDL_GL_DOUBLEBUFFER 5
#define SDL_WINDOWPOS_UNDEFINED 0
#define SDL_WINDOW_OPENGL 1
#define SDL_WINDOW_SHOWN 2
#define SDL_QUIT 256
void SDL_GetVersion(SDL_version *v);
char *SDL_getenv(const char *key);
int SDL_Init(Uint32 flags);
const char *SDL_GetCurrentVideoDriver(void);
int SDL_GL_SetAttribute(int key,int value);
SDL_Window *SDL_CreateWindow(const char *,int,int,int,int,Uint32);
SDL_GLContext SDL_GL_CreateContext(SDL_Window *);
int SDL_GL_MakeCurrent(SDL_Window *,SDL_GLContext);
int SDL_GL_SetSwapInterval(int);
void SDL_GL_GetDrawableSize(SDL_Window *,int *,int *);
Uint32 SDL_GetTicks(void);
int SDL_PollEvent(SDL_Event *);
void SDL_GL_SwapWindow(SDL_Window *);
void SDL_Delay(Uint32);
void SDL_ClearError(void);
const char *SDL_GetError(void);
void SDL_GL_DeleteContext(SDL_GLContext);
void SDL_DestroyWindow(SDL_Window *);
void SDL_Quit(void);
#endif
