# Python Day3 并发

## 1. 什么是进程与线程？

**进程：** 
可以把它理解为一个正在运行的“应用程序”实例。比如你打开了一个浏览器，操作系统就为它创建了一个进程，并分配了独立的内存空间和资源。进程是资源分配的最小单位，它们之间是相互独立的，就像车间与车间之间有墙隔开一样。

**线程：**
在一个进程内部，往往需要同时干好几件事。比如浏览器进程，既要负责从网络下载网页，又要负责渲染画面，还得响应你的鼠标点击。这些在进程内部同时运行的“子任务”，就是线程。线程是操作系统调度的最小单位。它们共享进程的内存资源，就像同一个车间里的工人共享工具和场地一样。

**简单总结：**
- 进程是“车间”，拥有独立的资源。
- 线程是“工人”，生活在车间里，共享车间资源。
- 一个进程至少包含一个线程（主线程）。

## 2. 这里的“同时”是真的同时吗？

我们常说的“多任务并行”，在单核 CPU 时代其实是做不到的，因为 CPU 同一时刻只能处理一个指令，操作系统通过快速地在不同任务间切换（时间片轮转），比如任务 A 做 0.01 秒，切换到任务 B 做 0.01 秒，以此类推。因为切换速度太快，肉眼感觉就像是同时在跑。

只有在现代的多核 CPU 上，才能实现真正的物理层面的“并行”。但在任务数量远超 CPU 核心数时，依然离不开操作系统的轮流调度。

## 3. Python 中的多线程（Threading）

在 Python 中，处理多任务的一种方式是使用线程。虽然 Python 的线程因为某些历史原因（GIL 锁）在 CPU 密集型任务上表现一般，但在处理 I/O 密集型任务（比如爬虫、文件读写）时依然非常高效。

线程不是生来就干活直到永远的，它有自己的生命周期：
- **新建**：刚被创建出来。
- **就绪**：准备好了，排队等着 CPU 临幸。
- **运行**：正在干活。
- **阻塞**：可能在等数据，或者被锁挡住了，暂时停工。
- **死亡**：任务完成或出师未捷身先死。

- **Join（等待）**：主线程通常跑得很快，如果不想主线程先溜走，导致子线程没干完活就被强制关闭，就需要用 `join` 方法。这就好比包工头（主线程）对工人（子线程）说：“你们干完活我再走。”
- **Daemon（守护/后台）**：有些线程是默默奉献的后台服务。如果把一个线程设置为守护线程，那么当主线程结束时，不管它有没有干完，都会随着主线程一起结束。这就好比皇上（主线程）驾崩，侍卫（守护线程）陪葬。
- **同步与锁（Lock）**：因为线程之间共享内存，经常会出现争抢资源的情况（比如两个线程同时修改一个变量）。为了避免数据打架，我们需要“锁”。一个线程抢到锁，锁上门干活，干完了开门释放锁，下一个线程才能进去。虽然安全了，但效率会降低。
- **通信（Queue/Event）**：线程之间也需要交流。最安全的方式是使用“队列（Queue）”，一个线程往里放数据，另一个拿数据，井井有条。也可以用事件（Event）来发信号。

### 创建线程

Python 内置了 `threading` 模块，我们可以很轻松地创建一个线程。最简单的方法是直接传入一个函数给 `Thread` 类。

```python
import threading
# 别import thread
import time

def sing(name):
    for i in range(3):
        print(f"{name} 正在唱歌... {i+1}")
        time.sleep(1)

def dance(name):
    for i in range(3):
        print(f"{name} 正在跳舞... {i+1}")
        time.sleep(1)

if __name__ == '__main__':
    # 创建线程
    t1 = threading.Thread(target=sing, args=("小明",))
    t2 = threading.Thread(target=dance, args=("小红",))
    
    # 启动线程
    t1.start()
    t2.start()
    
    print("主线程结束，但子线程可能还在跑...")
```

| 参数 | 含义 | 代码中的具体说明 |
| :--- | :--- | :--- |
| target | 指定线程启动后要执行的目标函数（仅写函数名，不加括号） | t1的target=sing：线程 1 启动后会执行sing函数；t2的target=dance：线程 2 执行dance函数 |
| args | 传递给target指定函数的参数元组（必须是元组类型） | args=("小明",)：给sing函数的name参数传值 “小明”；args=("小红",)：给dance函数传 “小红” |

- `target` 后只能写函数名（如`sing`），不能写`sing()`（加括号会直接在主线程执行函数，而非子线程）；
- `args` 必须是元组：即使只有 1 个参数，也要加逗号（如`("小明",)`），如果写成`("小明")`会被识别为字符串，而非元组，运行时会报错（函数需要 1 个参数，但传入了多个字符）；
- 如果目标函数有多个参数，`args` 按参数顺序传值即可，比如`args=(参数1, 参数2, 参数3)`。

#### Join（等待）

在上面的例子中，主线程可能打印完“主线程结束”就退出了，而子线程还在后台打印。如果我们希望主线程等待所有子线程干完活再一起收工，就需要用到 `join()`。

```python
    # ... 接上面的代码 ...
    t1.start()
    t2.start()
    
    # 阻塞主线程，先等 t1 跑完，再等 t2 跑完
    t1.join() #也就是主线程执行 t1.join()：暂停，等 t1 跑完
    t2.join()
    
    print("所有表演结束，大家一起谢幕！")
```

### Daemon（守护线程）

有些线程是默默奉献的后台服务（比如垃圾回收、心跳检测）。如果把一个线程设置为守护线程（Daemon），那么当主线程结束时，不管它有没有干完，都会随着主线程一起“殉葬”。

```python
import threading
import time

def work():
    print("我是守护线程，我开始干活了...")
    time.sleep(10) # 假设要干很久
    print("我是守护线程，我干完了！（你可能看不到这句）")

if __name__ == '__main__':
    t = threading.Thread(target=work)
    t.daemon = True # 必须在 start() 前设
    # t = threading.Thread(target=work, daemon=True)  # 也可以这样直接传参指定守护线程
    t.start()
    
    time.sleep(1)
    print("主线程结束了，守护线程也要挂了。")
```

### 同步与锁（Lock）

因为线程之间共享内存，经常会出现争抢资源的情况（比如两个线程同时修改一个全局变量）。为了避免数据错乱，我们需要“锁”。

```python
import threading

# 这是大家的共享资源
bank_balance = 0
# 创建一把锁
lock = threading.Lock()

def deposit(money):
    global bank_balance # 声明使用全局变量（否则会被当成局部变量报错 UnboundLocalError）
    for _ in range(100000):
        # 进门前先上锁
        lock.acquire() 
        try:
            bank_balance += money
        finally:
            # 无论如何都要记得开锁，不然就死锁了
            lock.release()

if __name__ == '__main__':
    t1 = threading.Thread(target=deposit, args=(1,))
    t2 = threading.Thread(target=deposit, args=(1,))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print(f"最终余额: {bank_balance}")
```

### 通信（Queue）

线程之间最安全的交流方式是使用“队列（Queue）”。它天然是线程安全的，不需要我们手动加锁。

```python
import threading
import queue
import time

def producer(q):
    for i in range(5):
        print(f"厨师做好了第 {i} 个包子")
        q.put(f"包子{i}")
        time.sleep(0.5)

def consumer(q):
    while True:
        food = q.get()
        if food is None:
            break
        print(f"顾客吃掉了 {food}")
        q.task_done()

if __name__ == '__main__':
    q = queue.Queue()
    
    t1 = threading.Thread(target=producer, args=(q,))
    t2 = threading.Thread(target=consumer, args=(q,))
    
    t1.start()
    t2.start()
    
    t1.join()
    # 给消费者发个信号说结束了（这里为了演示简单处理）
    q.put(None) 
    t2.join()
```

## 4. Python 中的多进程（Multiprocessing）

如果你想要充分利用多核 CPU 的计算能力（比如做大量的数学运算），Python 的多进程是更好的选择。

### Process 类

用法和线程几乎一模一样，只是换了个模块。

```python
import multiprocessing #好东西
import os

def run_proc(name):
    print(f'子进程 {name} 运行中，进程ID: {os.getpid()}...')

if __name__=='__main__':
    print(f'父进程 {os.getpid()}.')
    p = multiprocessing.Process(target=run_proc, args=('test',))
    print('子进程将要开始')
    p.start()
    p.join()
    print('子进程结束')
```

### 进程池（Pool）

如果你有成百上千个任务，手动创建进程太累且消耗资源。这时可以用“进程池”。

```python
from multiprocessing import Pool
import os, time, random

def long_time_task(name):
    print(f'任务 {name} (PID {os.getpid()}) 开始运行...')
    start = time.time()
    time.sleep(random.random() * 3)
    end = time.time()
    print(f'任务 {name} 运行了 {end - start:.2f} 秒.')

if __name__=='__main__':
    print(f'父进程 {os.getpid()}.')
    # 参数4表示“池子最多同时运行4个子进程”
    p = Pool(4)

    for i in range(5):
        p.apply_async(long_time_task, args=(i,))
    
    print('等待所有子进程完成...')
    p.close() # 关闭池子，不能再添加新任务了
    p.join()  # 等待所有任务完成
    print('所有任务完成.')
```

Pool 类还有一个同步方法 `apply()`

| 方法 | 执行方式 | 适用场景 |
| :--- | :--- | :--- |
| apply_async | 异步提交，提交后立刻返回，任务在子进程后台执行（并发） | 多任务并发执行（推荐） |
| apply | 同步提交，提交任务后阻塞父进程，直到该任务完成才返回（串行） | 需等待单个任务结果后再执行下一个 |

> 代码中如果把 `apply_async` 换成 `apply`，5 个任务会变成串行执行（一个做完再做下一个），完全失去多进程并发的意义。

### 进程间通信

因为进程内存独立，不能直接用全局变量通信。Python 提供了跨进程的 `Queue`。

```python
from multiprocessing import Process, Queue
import os, time, random

def write(q):
    print(f'写进程: {os.getpid()}')
    for value in ['A', 'B', 'C']:
        print(f'Put {value} to queue...')
        q.put(value)
        time.sleep(random.random())

def read(q):
    print(f'读进程: {os.getpid()}')
    while True:
        value = q.get(True)
        print(f'Get {value} from queue.')

if __name__=='__main__':
    # 父进程创建Queue，并传给各个子进程：
    q = Queue()
    # 直接在子进程创建 Queue 没用，因为进程内存独立
    pw = Process(target=write, args=(q,))
    pr = Process(target=read, args=(q,))
    # args=(q,) 把 Queue 实例传给子进程函数，这是子进程间能共享数据的唯一方式
    
    pw.start()
    pr.start()
    
    pw.join()
    # pr进程里是死循环，无法等待其结束，只能强行终止:
    pr.terminate()
```

`multiprocessing.Event` 确实是进程间通信 / 同步的工具，但它和 `Queue` 的核心定位不一样：

| 工具 | 核心作用 | 通信类型 | 典型场景 |
| :--- | :--- | :--- | :--- |
| Queue | 传递数据（如字符串、数字、对象） | 数据通信 | 写进程传数据给读进程、任务结果传递 |
| Event | 传递状态信号（“触发 / 未触发”） | 状态同步 | 控制子进程 “启动 / 暂停 / 停止”、多进程协同执行 |

- 初始状态为 `False`（未触发）；
- 父 / 子进程调用 `event.set()` → 开关打开（状态变为 `True`）；
- 父 / 子进程调用 `event.clear()` → 开关关闭（状态变回 `False`）；
- 子进程调用 `event.wait()` → 阻塞等待，直到开关被打开（状态为 `True`）。

```python
from multiprocessing import Process, Event
import time

def worker(event):
    print("子进程：等待启动信号...")
    event.wait()  # 阻塞，直到event被set()
    print("子进程：收到启动信号，开始干活！")
    time.sleep(2)
    print("子进程：干活完毕！")

if __name__ == '__main__':
    # 创建Event对象（初始False）
    event = Event()
    p = Process(target=worker, args=(event,))
    p.start()
    
    # 父进程延迟3秒发送启动信号
    time.sleep(3)
    print("父进程：发送启动信号！")
    event.set()  # 触发Event，子进程的wait()会解除阻塞
    
    p.join()
    print("所有进程结束")
```

## 总结

| 特性 | 多进程（Pool） | 多线程（threading） |
| :--- | :--- | :--- |
| 内存空间 | 每个进程有独立内存空间（不共享） | 所有线程共享进程的内存空间 |
| 数据共享 | 需用Queue/Pipe/Manager等 | 可直接共享全局变量（需加锁） |
| 开销 | 进程创建 / 销毁开销大，进程池复用更高效 | 线程创建 / 销毁开销小 |
| GIL 锁影响 | 不受 GIL 限制（可利用多核 CPU） | 受 GIL 限制（同一时间仅 1 线程执行 CPU 密集任务） |
| 适用场景 | CPU 密集型任务（如计算、耗时逻辑） | IO 密集型任务（如网络请求、文件读写） |

- **协作模式**：
    - **生产者-消费者模式**：这是一种经典的协作方式。一部分线程/进程负责生产数据（做包子），放入队列；另一部分负责处理数据（吃包子）。通过“条件变量（Condition）”或“队列”来协调供需平衡，避免撑死或饿死。

不管是多进程还是多线程，其本质都是为了压榨计算机的潜能，让程序跑得更欢快。但随之而来的是复杂度的提升（死锁、竞态条件等），所以“能力越大，责任越大”，使用时需格外小心。

### 附录：args 能传的内容

| 参数类型 | 示例 | 说明 |
| :--- | :--- | :--- |
| 基础类型 | `args=(1, "小明", 3.14)` | 数字、字符串等，按目标函数参数顺序传 |
| 容器类型 | `args=([1,2,3], {"name":"小红"})` | 列表、字典（进程间传的是副本，线程传的是引用） |
| 进程 / 线程工具 | `args=(q, event, lock)` | Queue、Event、Lock 等通信 / 同步工具 |
| 自定义对象 | `args=(MyClass(),)` | 自定义类的实例（需保证可序列化） |

> 还有一些杂七杂八的知识点主要涉及这些Thread、Process、Event、Queue的内置方法等，这个等用到的时候再学吧。
