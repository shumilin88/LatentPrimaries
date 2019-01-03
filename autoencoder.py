import numpy as np
import tensorflow as tf
import afqstensorutils as atu
from matplotlib import pylab as plt

def mygrad(y, x):
    yl = tf.unstack(y)
    gl = [ tf.gradients(_,x) for _ in yl ]
    return tf.stack(gl)

class Autoencoder(object):
    """
    A class for generating autoencoders.

    This parentclass is a linear map that's principal component analysis.
    """
    def __init__(self, size_x, size_q, data):
        self.size_x = size_x
        self.size_q = size_q
        self.dtype = tf.float32 # TODO check from data
        # Storage for my variables
        self.vars = {}
        # Make the trainer
        self.data = data
        self.goal = self.make_goal(data)
        self.train_step = self._make_train_step(data)
        # Make evaluating graphs
        self.i_x = tf.placeholder(name='i_x', shape=(None,size_x,), dtype=tf.float32 )
        self.o_q = self.encode( self.i_x, name='encode' )
        self.i_q = tf.placeholder(name='i_q', shape=(None,size_q,), dtype=tf.float32 )
        self.o_x = self.decode( self.i_q, name='decode' )
        self.o_grad_x = atu.vector_gradient(self.o_x, self.i_q)
        # Make the loggers for tensorboard
        
    def encode(self, x, name=None):
        W = self._var( "enc_W", (self.size_q, self.size_x) )
        b = self._var( "enc_b", (self.size_q,) )
        return tf.add(tf.matmul(W,x),b,name=name)
    
    def decode(self, q, name=None):
        W = self._var( "dec_W", (self.size_x, self.size_q) )
        b = self._var( "dec_b", (self.size_x,) )
        return tf.matmul(W,q)+b
    
    def make_goal(self, data):
        pred = self.decode(self.encode(data))
        p = tf.reduce_sum(tf.pow( data - pred, 2) ) 
        return p

    def _make_train_step(self, data):
        opt = tf.train.AdamOptimizer(1e-2)
        loss = self.make_goal(data)
        ts = opt.minimize(loss,global_step=tf.train.get_or_create_global_step())
        return ts
    
    def eval_q(self, i_x):
        return sess.eval( self.o_q, feed_dict={self.i_x:i_x} )

    def _var(self, name, shape, stddev=0.1):
        try:
            v = self.vars[name]
        except KeyError:
            v = tf.Variable(tf.truncated_normal(shape=shape, stddev=stddev),
                            name=name,
                            dtype=self.dtype)
            self.vars[name] = v
        return v
    
    def plot_distance(self, idxs=[0,1]):
        from matplotlib import pylab as plt
        XI,YI = idxs
        inputs = self.data.eval()
        q_enc = self.o_q.eval(feed_dict={self.i_x:inputs})
        x_dec = self.o_x.eval(feed_dict={self.i_q:q_enc})
        plt.plot( inputs[:,XI], inputs[:,YI],',')
        for a,b in zip(inputs,x_dec)[::10]:
            plt.plot( [a[XI],b[XI]], [a[YI],b[YI]],'-k')
        plt.plot(x_dec[:,XI],x_dec[:,YI],'+')
        plt.axis('square');
        
    def save_fit(self, fname, header,sess=None):
        qs = []
        for j in range(20):
            qs.append(self.o_q.eval(feed_dict={self.i_x:self.data.eval()}))
        qs = np.vstack(qs)
        if sess:
            xs = sess.run(self.o_x,feed_dict={self.i_q:qs})
        else:
            xs = self.o_x.eval(feed_dict={self.i_q:qs})
#         from matplotlib import pylab as plt
#         plt.plot(xs[:,0],xs[:,1],',')
        dat = np.hstack([xs,qs])
        np.savetxt(fname,dat,delimiter=", ",header=header,comments="")

        
class PolyAutoencoder(Autoencoder):
    """
    The basic implementation.
    """
    def __init__(self, size_x, size_q, data, Np_enc, Np_dec):
        self.Np_enc = Np_enc
        self.Np_dec = Np_dec
        Autoencoder.__init__(self,size_x, size_q, data)
        
    def encode(self, x, name=None):
        N_coeff = atu.Npolyexpand( self.size_x, self.Np_enc )
        We1 = self._var("enc_W", (N_coeff, self.size_q) )
        be1 = self._var("enc_b", (self.size_q,) )
        return tf.matmul( atu.polyexpand(x, self.Np_enc), We1 ) + be1
    
    def decode(self, q, name=None):
        N_coeff = atu.Npolyexpand( self.size_q, self.Np_dec )
        We1 = self._var("dec_W", (N_coeff, self.size_x) )
        be1 = self._var("dec_b", (self.size_x,) )
        return tf.matmul( atu.polyexpand(q, self.Np_dec), We1 ) + be1
    
class DeepPolyAutoencoder(Autoencoder):
    """
    The Deep relu'ed layers on each side
    TODO
    """
    def __init__(self, size_x, size_q, data, Np_enc, enc_layers, Np_dec, dec_layers):
        self.Np_enc = Np_enc
        self.Np_dec = Np_dec
        self.enc_layers = enc_layers
        self.dec_layers = dec_layers
        Autoencoder.__init__(self,size_x, size_q, data)
        
    def encode(self, x, name=None):
        N_coeff = atu.Npolyexpand( self.size_x, self.Np_enc )
        for hidden_size in enc_layers + [self.size_q]:
            We1 = self._var("enc_W", (N_coeff, self.size_q) )
            be1 = self._var("enc_b", (self.size_q,) )
        return tf.matmul( atu.polyexpand(x, self.Np_enc), We1 ) + be1
    
    def decode(self, q, name=None):
        N_coeff = atu.Npolyexpand( self.size_q, self.Np_dec )
        We1 = self._var("dec_W", (N_coeff, self.size_x) )
        be1 = self._var("dec_b", (self.size_x,) )
        return tf.matmul( atu.polyexpand(q, self.Np_dec), We1 ) + be1
    
class ClassifyingPolyAutoencoder(Autoencoder):
    """
    This one is like the PolyAutoencoder, but has a classifying branch

    The idea is that this one learns piecewise branching logic.
    
    x > E > z -> Npoly ->   W1        -> * -> x
                  `-> W2->relu->softmax -^ (phase)
    
    """
    activations={
        'tanh':tf.tanh,
        'sigmoid':tf.sigmoid,
        'relu':tf.nn.relu
    }
    def __init__(self, size_x, size_q, data, p_enc, p_dec, N_curve, N_bound,
                 boundary_activation='tanh',softmax_it=True):
        self.Np_enc = p_enc
        self.Np_dec = p_dec

        self.N_curve = N_curve
        self.N_bound = N_bound
        self.boundary_activation = boundary_activation
        self.softmax_it = softmax_it
        Autoencoder.__init__(self,size_x, size_q, data)
        self.o_class = self.classify(self.i_q)
        
    def encode(self, x, name=None):
        N_coeff = atu.Npolyexpand( self.size_x, self.Np_enc )
        W = self._var("enc_W", (N_coeff, self.size_q) )
        b = self._var("enc_b", (self.size_q,) )
        return tf.add(tf.matmul( atu.polyexpand(x, self.Np_enc), W ), b, name=name)
    
    def classify(self, q, name=None):
        qpoly = atu.polyexpand(q, self.Np_dec)
        N_coeff = atu.Npolyexpand( self.size_q, self.Np_dec )

        W2 = self._var("dec_W_bound", (N_coeff, self.N_bound) )
        b2 = self._var("dec_b_bound", (self.N_bound,) )
        act = self.activations[self.boundary_activation]
        h_bound = act(tf.tensordot(qpoly,W2,axes=[-1,0])+b2)
        
        W_select = self._var("dec_W_select", (self.N_bound,self.N_curve))
        h_select = tf.tensordot(h_bound,W_select, axes=[-1,0],
                                name=(name if not self.softmax_it else None))
        if self.softmax_it:
            h_select = tf.nn.softmax(h_select, name=name)
        return h_select
    
    def decode(self, q, name=None):
        qpoly = atu.polyexpand(q, self.Np_dec)
        N_coeff = atu.Npolyexpand( self.size_q, self.Np_dec )
        
        W1 = self._var("dec_W_curve", (N_coeff, self.N_curve, self.size_x) )
        b1 = self._var("dec_b_curve", (self.N_curve, self.size_x) )
        h_curve = tf.tensordot(qpoly,W1,axes=[-1,0])+b1
        
        h_select = self.classify(q)
        
        x = tf.einsum('ijk,ij->ik',h_curve,h_select)
        return tf.identity(x,name=name)
    
    def save_fit(self, fname, header,sess=None):
        qs = []
        ixs = []
        def myev(x,feed_dict={}):
            if sess:
                return sess.run(x,feed_dict=feed_dict)
            else:
                return x.eval(feed_dict=feed_dict)
        for j in range(20):
            ix = myev(self.data)
            qs.append(myev(self.o_q,feed_dict={self.i_x:ix}))
            ixs.append(ix)
        qs = np.vstack(qs)
        ixs = np.vstack(ixs)
        oxs = myev(self.o_x,{self.i_q:qs})
        probs = myev(self.o_class,feed_dict={self.i_q:qs})
        classes = probs.argmax(axis=-1)
        errors = ((ixs-oxs)**2).sum(axis=-1)
        
        from matplotlib import pylab as plt
        plt.plot(oxs[:,0],oxs[:,1],',')
        
        dat = np.hstack([oxs,qs,classes.reshape((-1,1)), errors.reshape(-1,1)])
        extra_header = ", "+", ".join(["q{0}".format(i) for i in range(self.size_q)]) + ", class, error"
        np.savetxt(fname,dat,delimiter=", ",header=header+extra_header,comments="")
