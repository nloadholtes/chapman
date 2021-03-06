from chapman.task import Task, Function
from chapman.decorators import task
from chapman import model as M
from chapman import exc

from .test_base import TaskTest

class TestBasic(TaskTest):

    def test_curry(self):
        t = self.doubler.n(4)
        t.start()
        self._handle_messages()
        t.refresh()
        self.assertEqual(8, t.result.get())

    def test_abstract_task(self):
        t = Task.new({})
        with self.assertRaises(NotImplementedError):
            t.run(None)

    def test_call_direct(self):
        self.assertEqual(4, self.doubler(2))

    def test_create_task(self):
        self.doubler.n()
        self.assertEqual(1, M.TaskState.m.find().count())

    def test_deco_task(self):
        from chapman.task.t_func import FunctionTaskWrapper
        @task()
        def foo():
            pass
        self.assertIsInstance(foo, FunctionTaskWrapper)

    def test_create_message(self):
        t = self.doubler.n()
        msg = M.Message.n(t, 'run', 1, 2, a=3)
        self.assertEqual(msg.task_id, t.id)
        self.assertEqual(msg.task_repr, repr(t))
        self.assertEqual(msg.schedule.status, 'pending')
        self.assertEqual(msg.slot, 'run')
        self.assertEqual(msg.args, (1,2))
        self.assertEqual(msg.kwargs, {'a': 3})
        self.assertEqual(1, M.Message.m.find().count())
        
    def test_start(self):
        t = self.doubler.n()
        msg = t.start(2)
        self.assertEqual(msg.task_id, t.id)
        self.assertEqual(msg.schedule.status, 'ready')
        self.assertEqual(msg.slot, 'run')
        self.assertEqual(msg.args, (2,))
        self.assertEqual(msg.kwargs, {})
        self.assertEqual(1, M.Message.m.find().count())

    def test_run_message(self):
        t = self.doubler.n()
        msg = t.start(2)
        t.handle(msg)
        self.assertEqual(t.result.get(), 4)
        self.assertEqual(M.Message.m.find().count(), 0)
        self.assertEqual(M.TaskState.m.find().count(), 1)

    def test_run_message_error(self):
        t = self.doubler.n()
        msg = t.start(None)
        t.handle(msg)
        self.assertEqual(M.Message.m.find().count(), 0)
        self.assertEqual(M.TaskState.m.find().count(), 1)
        with self.assertRaises(exc.TaskError) as err:
            t.result.get()
        assert 'TypeError' in repr(err.exception)
        self.assertEqual(err.exception.args[0], TypeError)

    def test_ignore_result(self):
        t = self.doubler.new(ignore_result=True)
        msg = t.start(2)
        self.assertEqual(1, M.Message.m.find().count())
        self.assertEqual(1, M.TaskState.m.find().count())
        t.handle(msg)
        self.assertEqual(0, M.Message.m.find().count())
        self.assertEqual(0, M.TaskState.m.find().count())
        
    def test_run_message_callback(self):
        @Function.decorate('doubler_result')
        def doubler_result(result):
            return result.get() * 2
        t0 = self.doubler.new(ignore_result=True)
        t1 = doubler_result.n()
        t0.link(t1, 'run')
        t0.start(2)
        self.assertEqual(2, M.Message.m.find().count())

        m,s = M.Message.reserve('foo', ['chapman'])
        t = Task.from_state(s)
        t.handle(m)

        m,s = M.Message.reserve('foo', ['chapman'])
        t = Task.from_state(s)
        t.handle(m)
        self.assertEqual(t.result.get(), 8)
        self.assertEqual(M.Message.m.find().count(), 0)
        self.assertEqual(M.TaskState.m.find().count(), 1)

    def test_run_message_callback_error(self):
        t0 = self.doubler.n()
        t1 = self.doubler.n()
        t0.link(t1, 'run')
        t0.start(None)
        self.assertEqual(2, M.Message.m.find().count())

        m,s = M.Message.reserve('foo', ['chapman'])
        t = Task.from_state(s)
        t.handle(m)

        m,s = M.Message.reserve('foo', ['chapman'])
        t = Task.from_state(s)
        t.handle(m)

        with self.assertRaises(exc.TaskError):
            t.result.get()
        
    def test_run_message_callback_failed_not_immutable(self):
        t0 = self.doubler.n()
        t1 = self.doubler.n(4)
        t0.link(t1, 'run')
        t0.start(1)

        self._handle_messages()
        t1.refresh()

        with self.assertRaises(exc.TaskError) as te:
            t1.result.get()
        self.assertEqual(te.exception.args[0], TypeError)
        
    def test_run_message_callback_immutable(self):
        t0 = self.doubler.n()
        t1 = self.doubler.ni(14)
        t0.link(t1, 'run')
        t0.start(1)
        
        self._handle_messages()
        t1.refresh()

        self.assertEqual(t1.result.get(), 28)
